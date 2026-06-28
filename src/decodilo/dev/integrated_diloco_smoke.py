"""Bounded local integrated DiLoCo synthetic smoke command."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.diloco_optimizer_smoke import (
    EXPECTED_POST_INNER_PARAMETERS,
    EXPECTED_POST_OUTER_PARAMETERS,
    EXPECTED_PSEUDO_GRADIENT,
    INITIAL_PARAMETERS,
    SYNTHETIC_GRADIENT,
    _adamw_reference_step,
    _max_abs_delta,
    _nested_float_close,
    _nesterov_reference_step,
)
from decodilo.runtime.update_stream import UpdateStream
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.replay import replay_events
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge

IntegratedDilocoSmokeStatus = Literal["passed", "failed"]
OptimizationFidelity = Literal[
    "integrated_optimizer_protocol_smoke",
    "partial_integrated_optimizer_protocol_smoke",
    "not_verified",
]
ParameterFragmentSemantics = Literal["not_exercised", "true_model_fragment"]


class IntegratedDilocoSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    integrated_diloco_smoke_status: IntegratedDilocoSmokeStatus
    command: str = "dev integrated-diloco-smoke"
    synthetic: bool
    learners_requested: int
    sync_rounds_requested: int
    max_steps: int
    inner_optimizer_requested: str
    outer_optimizer_requested: str
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    real_model_training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    learner_count_observed: int = 0
    syncer_role_check_passed: bool | None = None
    learner_syncer_exchange_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    sync_rounds_completed: int = 0
    global_version_before: int | None = None
    global_version_after: int | None = None
    synthetic_updates_produced: int = 0
    synthetic_updates_accepted: int = 0
    synthetic_updates_rejected: int = 0
    useful_synthetic_tokens: int | None = None
    useful_synthetic_tokens_reason: str | None = None
    stale_update_count: int | None = None
    stale_update_count_reason: str | None = None
    duplicate_update_count: int | None = None
    duplicate_update_count_reason: str | None = None
    optimization_fidelity: OptimizationFidelity
    inner_optimizer_semantics: Literal["adamw", "not_exercised"]
    outer_optimizer_semantics: Literal["nesterov", "not_exercised"]
    parameter_fragment_semantics: ParameterFragmentSemantics = "not_exercised"
    pseudo_gradient_check_passed: bool = False
    inner_adamw_check_passed: bool = False
    outer_nesterov_check_passed: bool = False
    optimizer_state_roundtrip_check_passed: bool = False
    reference_value_check_passed: bool = False
    protocol_optimizer_link_check_passed: bool = False
    tolerance: float = 1e-12
    max_abs_error: float | None = None
    initial_parameters: list[float] = Field(default_factory=list)
    synthetic_gradient: list[float] = Field(default_factory=list)
    post_inner_parameters: list[float] = Field(default_factory=list)
    pseudo_gradient: list[float] = Field(default_factory=list)
    post_outer_parameters: list[float] = Field(default_factory=list)
    expected_post_outer_parameters: list[float] = Field(default_factory=list)
    protocol_committed_parameters: list[float] = Field(default_factory=list)
    inner_hyperparameters: dict[str, float] = Field(default_factory=dict)
    outer_hyperparameters: dict[str, float] = Field(default_factory=dict)
    optimizer_state_roundtrip: dict[str, Any] = Field(default_factory=dict)
    pseudo_gradient_convention: str | None = None
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None
    runtime_checks: dict[str, bool | int | float | str] = Field(default_factory=dict)
    modules_imported: list[str] = Field(default_factory=list)
    skipped_checks: dict[str, str] = Field(default_factory=dict)
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error_message: str | None = None
    artifact_bytes: int = 0
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> IntegratedDilocoSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("integrated DiLoCo smoke report cannot enable launch")
        if (
            self.network_used
            or self.package_install_attempted
            or self.download_attempted
            or self.training_attempted
            or self.real_model_training_attempted
            or self.torch_required
            or self.gpu_required
            or self.background_process_started
        ):
            raise ValueError("integrated DiLoCo smoke report cannot require unsafe behavior")
        if (
            self.optimization_fidelity == "integrated_optimizer_protocol_smoke"
            and (
                self.inner_optimizer_semantics != "adamw"
                or self.outer_optimizer_semantics != "nesterov"
                or not self.learner_syncer_exchange_check_passed
                or not self.update_or_commit_check_passed
                or not self.replay_or_metric_check_passed
                or not self.pseudo_gradient_check_passed
                or not self.inner_adamw_check_passed
                or not self.outer_nesterov_check_passed
                or not self.optimizer_state_roundtrip_check_passed
                or not self.reference_value_check_passed
                or not self.protocol_optimizer_link_check_passed
            )
        ):
            raise ValueError(
                "integrated optimizer/protocol smoke requires protocol and optimizer checks"
            )
        if self.parameter_fragment_semantics == "true_model_fragment":
            raise ValueError("true model fragment semantics are not exercised here")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_integrated_diloco_smoke(
    *,
    synthetic: bool,
    learners: int,
    sync_rounds: int,
    inner_optimizer: str,
    outer_optimizer: str,
    max_steps: int,
    out: str | Path,
) -> IntegratedDilocoSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    if not synthetic:
        errors.append("Integrated DiLoCo smoke requires --synthetic")
    if learners != 1:
        errors.append("Integrated DiLoCo smoke currently requires --learners 1")
    if sync_rounds != 1:
        errors.append("Integrated DiLoCo smoke currently requires --sync-rounds 1")
    if inner_optimizer != "adamw":
        errors.append("Integrated DiLoCo smoke currently requires --inner-optimizer adamw")
    if outer_optimizer != "nesterov":
        errors.append("Integrated DiLoCo smoke currently requires --outer-optimizer nesterov")
    if max_steps != 1:
        errors.append("Integrated DiLoCo smoke currently requires --max-steps 1")

    if not errors:
        try:
            metrics = _run_integrated_optimizer_protocol_smoke()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"integrated_diloco_smoke_failed:{type(exc).__name__}")

    exchange_passed = bool(metrics.get("learner_syncer_exchange_check_passed", False))
    update_passed = bool(metrics.get("update_or_commit_check_passed", False))
    replay_passed = bool(metrics.get("replay_or_metric_check_passed", False))
    pseudo_passed = bool(metrics.get("pseudo_gradient_check_passed", False))
    inner_passed = bool(metrics.get("inner_adamw_check_passed", False))
    outer_passed = bool(metrics.get("outer_nesterov_check_passed", False))
    roundtrip_passed = bool(metrics.get("optimizer_state_roundtrip_check_passed", False))
    reference_passed = bool(metrics.get("reference_value_check_passed", False))
    link_passed = bool(metrics.get("protocol_optimizer_link_check_passed", False))
    all_checks_passed = (
        not errors
        and exchange_passed
        and update_passed
        and replay_passed
        and pseudo_passed
        and inner_passed
        and outer_passed
        and roundtrip_passed
        and reference_passed
        and link_passed
    )
    partial_checks_passed = not all_checks_passed and any(
        [
            exchange_passed,
            update_passed,
            replay_passed,
            pseudo_passed,
            inner_passed,
            outer_passed,
            roundtrip_passed,
            reference_passed,
            link_passed,
        ]
    )
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = IntegratedDilocoSmokeReport(
        integrated_diloco_smoke_status="passed" if all_checks_passed else "failed",
        synthetic=synthetic,
        learners_requested=learners,
        sync_rounds_requested=sync_rounds,
        max_steps=max_steps,
        inner_optimizer_requested=inner_optimizer,
        outer_optimizer_requested=outer_optimizer,
        learner_count_observed=int(metrics.get("learner_count_observed", 0)),
        syncer_role_check_passed=bool(metrics.get("syncer_role_check_passed", False)),
        learner_syncer_exchange_check_passed=exchange_passed,
        update_or_commit_check_passed=update_passed,
        sync_rounds_completed=int(metrics.get("sync_rounds_completed", 0)),
        global_version_before=metrics.get("global_version_before"),
        global_version_after=metrics.get("global_version_after"),
        synthetic_updates_produced=int(metrics.get("synthetic_updates_produced", 0)),
        synthetic_updates_accepted=int(metrics.get("synthetic_updates_accepted", 0)),
        synthetic_updates_rejected=int(metrics.get("synthetic_updates_rejected", 0)),
        useful_synthetic_tokens=metrics.get("useful_synthetic_tokens"),
        useful_synthetic_tokens_reason=None
        if "useful_synthetic_tokens" in metrics
        else "not meaningful because integrated smoke did not complete",
        stale_update_count=metrics.get("stale_update_count"),
        stale_update_count_reason=None
        if "stale_update_count" in metrics
        else "not meaningful because update stream did not complete",
        duplicate_update_count=metrics.get("duplicate_update_count"),
        duplicate_update_count_reason=None
        if "duplicate_update_count" in metrics
        else "not meaningful because update stream did not complete",
        optimization_fidelity=(
            "integrated_optimizer_protocol_smoke"
            if all_checks_passed
            else (
                "partial_integrated_optimizer_protocol_smoke"
                if partial_checks_passed
                else "not_verified"
            )
        ),
        inner_optimizer_semantics="adamw" if inner_passed else "not_exercised",
        outer_optimizer_semantics="nesterov" if outer_passed else "not_exercised",
        parameter_fragment_semantics="not_exercised",
        pseudo_gradient_check_passed=pseudo_passed,
        inner_adamw_check_passed=inner_passed,
        outer_nesterov_check_passed=outer_passed,
        optimizer_state_roundtrip_check_passed=roundtrip_passed,
        reference_value_check_passed=reference_passed,
        protocol_optimizer_link_check_passed=link_passed,
        max_abs_error=metrics.get("max_abs_error"),
        initial_parameters=list(metrics.get("initial_parameters", [])),
        synthetic_gradient=list(metrics.get("synthetic_gradient", [])),
        post_inner_parameters=list(metrics.get("post_inner_parameters", [])),
        pseudo_gradient=list(metrics.get("pseudo_gradient", [])),
        post_outer_parameters=list(metrics.get("post_outer_parameters", [])),
        expected_post_outer_parameters=list(
            metrics.get("expected_post_outer_parameters", [])
        ),
        protocol_committed_parameters=list(metrics.get("protocol_committed_parameters", [])),
        inner_hyperparameters=dict(metrics.get("inner_hyperparameters", {})),
        outer_hyperparameters=dict(metrics.get("outer_hyperparameters", {})),
        optimizer_state_roundtrip=dict(metrics.get("optimizer_state_roundtrip", {})),
        pseudo_gradient_convention=metrics.get("pseudo_gradient_convention"),
        replay_or_metric_check_passed=replay_passed,
        artifact_or_report_check_passed=False,
        runtime_checks={
            key: value
            for key, value in metrics.items()
            if isinstance(value, bool | int | float | str)
        },
        modules_imported=[
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
            "decodilo.syncer.token_weighted_merge",
            "decodilo.syncer.outer_optimizer",
            "decodilo.dev.diloco_optimizer_smoke",
        ],
        skipped_checks={
            "full_diloco_training": (
                "not claimed; this smoke integrates local synthetic protocol and "
                "optimizer semantics only"
            ),
            "real_model_training": "forbidden for integrated smoke",
            "parameter_fragment_semantics": (
                "not exercised; tiny numeric vectors are used instead of true "
                "model/tensor fragments"
            ),
            "communication_overlap": "not exercised by this bounded local smoke",
            "quantized_communication": "not exercised by this bounded local smoke",
            "network": "forbidden for integrated smoke",
            "gpu": "not required for integrated smoke",
            "torch": "not required for integrated smoke",
        },
        failed_check=failed_check,
        error_classification=error_classification,
        safe_error_message=safe_error_message,
        elapsed_seconds=max(0.0, time.monotonic() - start),
        errors=errors,
    )
    report = _with_stable_artifact_size(report)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    loaded = load_integrated_diloco_smoke_report(target)
    artifact_report_passed = (
        loaded.integrated_diloco_smoke_status == report.integrated_diloco_smoke_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 32_768
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_integrated_diloco_smoke_report(
    path: str | Path,
) -> IntegratedDilocoSmokeReport:
    return IntegratedDilocoSmokeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_integrated_optimizer_protocol_smoke() -> dict[str, Any]:
    tolerance = 1e-12
    learner_id = "learner-0"
    round_id = "integrated-diloco-round-0"
    global_version_before = 0
    global_version_after = 1
    useful_tokens = 21
    inner_hyperparameters = {
        "learning_rate": 0.01,
        "beta1": 0.9,
        "beta2": 0.999,
        "epsilon": 1e-8,
        "weight_decay": 0.01,
    }
    outer_hyperparameters = {
        "learning_rate": 0.5,
        "momentum": 0.9,
    }
    inner_state_before = {
        "step": 0,
        "m": [0.0 for _ in INITIAL_PARAMETERS],
        "v": [0.0 for _ in INITIAL_PARAMETERS],
    }
    post_inner, inner_state_after = _adamw_reference_step(
        parameters=INITIAL_PARAMETERS,
        gradient=SYNTHETIC_GRADIENT,
        state=inner_state_before,
        learning_rate=inner_hyperparameters["learning_rate"],
        beta1=inner_hyperparameters["beta1"],
        beta2=inner_hyperparameters["beta2"],
        epsilon=inner_hyperparameters["epsilon"],
        weight_decay=inner_hyperparameters["weight_decay"],
    )
    pseudo_gradient = [
        before - after
        for before, after in zip(INITIAL_PARAMETERS, post_inner, strict=True)
    ]
    outer_state_before = {
        "step": 0,
        "velocity": [0.0 for _ in INITIAL_PARAMETERS],
    }
    post_outer, outer_state_after = _nesterov_reference_step(
        parameters=INITIAL_PARAMETERS,
        pseudo_gradient=pseudo_gradient,
        state=outer_state_before,
        learning_rate=outer_hyperparameters["learning_rate"],
        momentum=outer_hyperparameters["momentum"],
    )

    base_vector = np.asarray(INITIAL_PARAMETERS, dtype=np.float64)
    learner_vector = np.asarray(post_inner, dtype=np.float64)
    merge = token_weighted_merge(
        base_vector,
        [
            LearnerDelta(
                learner_id=learner_id,
                vector=learner_vector,
                tokens=useful_tokens,
                global_version_seen=global_version_before,
            )
        ],
        optimizer=SGDOuterOptimizer(outer_lr=1.0),
    )

    async def update_delivery() -> dict[str, bool | int]:
        stream = UpdateStream(max_version_lag=1)
        stream.register(learner_id, version=global_version_before)
        pending_update = asyncio.create_task(
            stream.wait_for_update(
                learner_id=learner_id,
                learner_version=global_version_before,
                current_version=global_version_before,
                timeout_seconds=1.0,
            )
        )
        await asyncio.sleep(0)
        pre_commit_wait_pending = not pending_update.done()
        stream.notify_commit(global_version=global_version_after)
        update_ready = await asyncio.wait_for(pending_update, timeout=1.0)
        stream.mark_sent(learner_id, global_version=global_version_after)
        stream.ack(
            learner_id,
            global_version=global_version_after,
            current_version=global_version_after,
        )
        stale = stream.stale_learners(current_version=global_version_after)
        stream_metrics = stream.metrics_dict()
        return {
            "update_stream_pre_commit_wait_pending": pre_commit_wait_pending,
            "update_ready_after_commit": update_ready is True,
            "global_update_broadcasts": int(stream_metrics["global_update_broadcasts"]),
            "global_update_messages_sent": int(
                stream_metrics["global_update_messages_sent"]
            ),
            "global_update_acks": int(stream_metrics["global_update_acks"]),
            "duplicate_update_count": int(
                stream_metrics["duplicate_global_update_acks"]
            ),
            "stale_update_count": len(stale),
            "learner_lag_zero": stream.learner_update_lag_current == {learner_id: 0},
        }

    update_metrics = asyncio.run(update_delivery())
    log = EventLog(path=None, run_id="integrated-diloco-smoke")
    log.append(
        EventType.LEARNER_STARTED,
        logical_time=0,
        learner_id=learner_id,
        payload={
            "learner_id": learner_id,
            "global_version_seen": global_version_before,
            "synthetic_local_steps": 1,
            "optimization_fidelity": "integrated_optimizer_protocol_smoke",
            "inner_optimizer_semantics": "adamw",
        },
    )
    log.append(
        EventType.LEARNER_FRAGMENT_SUBMITTED,
        logical_time=1,
        learner_id=learner_id,
        payload={
            "learner_id": learner_id,
            "global_version_seen": global_version_before,
            "tokens": useful_tokens,
            "vector": learner_vector.tolist(),
            "initial_parameters": INITIAL_PARAMETERS,
            "post_inner_parameters": post_inner,
            "pseudo_gradient": pseudo_gradient,
            "synthetic_gradient": SYNTHETIC_GRADIENT,
            "inner_optimizer_semantics": "adamw",
        },
    )
    log.append(
        EventType.SYNC_ROUND_STARTED,
        logical_time=2,
        round_id=round_id,
        payload={
            "round_id": round_id,
            "previous_global_version": global_version_before,
            "accepted_learner_ids": [learner_id],
            "syncer_role": "single_local_synthetic_syncer",
            "outer_optimizer_semantics": "nesterov_reference_smoke",
        },
    )
    log.append(
        EventType.SYNC_ROUND_COMMITTED,
        logical_time=3,
        round_id=round_id,
        payload={
            "round_id": round_id,
            "previous_global_version": global_version_before,
            "new_global_version": global_version_after,
            "accepted_learner_ids": [learner_id],
            "useful_tokens": useful_tokens,
            "outer_lr": 1.0,
            "old_global_vector": base_vector.tolist(),
            "weighted_delta": merge.weighted_delta.tolist(),
            "new_global_vector": merge.new_global_vector.tolist(),
            "outer_optimizer_semantics": "token_weighted_merge_for_protocol_commit",
            "nesterov_reference_post_outer": post_outer,
        },
    )
    log.append(
        EventType.GLOBAL_UPDATE_SENT,
        logical_time=4,
        learner_id=learner_id,
        payload={"learner_id": learner_id, "global_version": global_version_after},
    )
    log.append(
        EventType.GLOBAL_UPDATE_ACKED,
        logical_time=5,
        learner_id=learner_id,
        payload={"learner_id": learner_id, "global_version": global_version_after},
    )
    replay = replay_events(log.events)
    if replay.final_global_vector is None:
        raise AssertionError("integrated DiLoCo replay did not produce final vector")
    if not np.allclose(replay.final_global_vector, merge.new_global_vector):
        raise AssertionError("integrated DiLoCo replay final vector mismatch")

    inner_error = _max_abs_delta(post_inner, EXPECTED_POST_INNER_PARAMETERS)
    pseudo_error = _max_abs_delta(pseudo_gradient, EXPECTED_PSEUDO_GRADIENT)
    outer_error = _max_abs_delta(post_outer, EXPECTED_POST_OUTER_PARAMETERS)
    protocol_error = _max_abs_delta(merge.new_global_vector.tolist(), post_inner)
    max_abs_error = max(inner_error, pseudo_error, outer_error, protocol_error)
    optimizer_state_roundtrip = {
        "inner_adamw": inner_state_after,
        "outer_nesterov": outer_state_after,
    }
    roundtripped_state = json.loads(json.dumps(optimizer_state_roundtrip, sort_keys=True))
    roundtrip_passed = _nested_float_close(
        optimizer_state_roundtrip,
        roundtripped_state,
        tolerance=tolerance,
    )
    return {
        **update_metrics,
        "learner_count_observed": len(merge.included_learner_ids),
        "syncer_role_check_passed": replay.sync_rounds_committed == 1,
        "learner_syncer_exchange_check_passed": replay.accepted_useful_tokens
        == useful_tokens,
        "update_or_commit_check_passed": (
            update_metrics["global_update_acks"] == 1
            and global_version_after == global_version_before + 1
        ),
        "replay_or_metric_check_passed": replay.accepted_useful_tokens == useful_tokens,
        "sync_rounds_completed": replay.sync_rounds_committed,
        "global_version_before": global_version_before,
        "global_version_after": global_version_after,
        "synthetic_updates_produced": 1,
        "synthetic_updates_accepted": 1,
        "synthetic_updates_rejected": replay.rejected_update_count,
        "useful_synthetic_tokens": replay.accepted_useful_tokens,
        "event_log_event_count": len(log.events),
        "synthetic_local_steps_completed": 1,
        "initial_parameters": INITIAL_PARAMETERS,
        "synthetic_gradient": SYNTHETIC_GRADIENT,
        "post_inner_parameters": post_inner,
        "pseudo_gradient": pseudo_gradient,
        "post_outer_parameters": post_outer,
        "expected_post_outer_parameters": EXPECTED_POST_OUTER_PARAMETERS,
        "protocol_committed_parameters": merge.new_global_vector.tolist(),
        "inner_hyperparameters": inner_hyperparameters,
        "outer_hyperparameters": outer_hyperparameters,
        "optimizer_state_roundtrip": optimizer_state_roundtrip,
        "pseudo_gradient_convention": (
            "pseudo_gradient = initial_parameters - post_inner_parameters; "
            "learner protocol submission uses post_inner_parameters"
        ),
        "inner_adamw_check_passed": inner_error <= tolerance,
        "pseudo_gradient_check_passed": pseudo_error <= tolerance,
        "outer_nesterov_check_passed": outer_error <= tolerance,
        "optimizer_state_roundtrip_check_passed": roundtrip_passed,
        "reference_value_check_passed": max_abs_error <= tolerance and roundtrip_passed,
        "protocol_optimizer_link_check_passed": protocol_error <= tolerance,
        "max_abs_error": max_abs_error,
        "final_protocol_vector_l2": float(np.linalg.norm(replay.final_global_vector)),
        "weighted_delta_l2": float(np.linalg.norm(merge.weighted_delta)),
        "token_weight_learner_0": float(merge.token_weights[learner_id]),
    }


def _with_stable_artifact_size(
    report: IntegratedDilocoSmokeReport,
) -> IntegratedDilocoSmokeReport:
    current = report
    for _ in range(8):
        size = len(current.to_json().encode("utf-8"))
        if size == current.artifact_bytes:
            return current
        current = current.model_copy(update={"artifact_bytes": size})
    return current


def _classify_failure(errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not errors:
        return None, None, None
    first = errors[0]
    if first.startswith("Integrated DiLoCo smoke requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("Integrated DiLoCo smoke currently requires"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("integrated_diloco_smoke_failed:"):
        return (
            "integrated_protocol_optimizer_check",
            "integrated_diloco_smoke_failed",
            first,
        )
    return "integrated_diloco_smoke", "integrated_diloco_smoke_failed", first
