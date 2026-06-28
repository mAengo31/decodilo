"""Bounded local DiLoCo-shaped synthetic protocol smoke command."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.update_stream import UpdateStream
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.replay import replay_events
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge

DilocoSmokeStatus = Literal["passed", "failed"]
OptimizationFidelity = Literal[
    "full_diloco",
    "diloco_shaped_protocol_only",
    "not_applicable",
]
InnerOptimizerSemantics = Literal["adamw", "synthetic_placeholder", "not_exercised"]
OuterOptimizerSemantics = Literal[
    "nesterov",
    "token_weighted_merge",
    "sgd_like",
    "synthetic_placeholder",
    "not_exercised",
]
ParameterFragmentSemantics = Literal[
    "true_model_fragment",
    "storage_chunk_only",
    "not_exercised",
]


class DilocoSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    diloco_smoke_status: DilocoSmokeStatus
    command: str = "dev diloco-smoke"
    synthetic: bool
    learners_requested: int
    sync_rounds_requested: int
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    real_model_training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    diloco_shape_check_passed: bool | None = None
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
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None
    optimization_fidelity: OptimizationFidelity
    inner_optimizer_semantics: InnerOptimizerSemantics
    outer_optimizer_semantics: OuterOptimizerSemantics
    parameter_fragment_semantics: ParameterFragmentSemantics
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
    def _validate_disabled(self) -> DilocoSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("DiLoCo smoke report cannot enable launch")
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
            raise ValueError("DiLoCo smoke report cannot require unsafe behavior")
        if (
            self.optimization_fidelity == "full_diloco"
            and (
                self.inner_optimizer_semantics != "adamw"
                or self.outer_optimizer_semantics != "nesterov"
            )
        ):
            raise ValueError("full DiLoCo fidelity requires AdamW and Nesterov semantics")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_diloco_smoke(
    *,
    synthetic: bool,
    learners: int,
    sync_rounds: int,
    max_steps: int,
    out: str | Path,
) -> DilocoSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    runtime_checks: dict[str, bool | int | float | str] = {}
    metrics: dict[str, bool | int | float | str] = {}
    if not synthetic:
        errors.append("DiLoCo smoke requires --synthetic")
    if learners != 1:
        errors.append("DiLoCo smoke currently requires --learners 1")
    if sync_rounds != 1:
        errors.append("DiLoCo smoke currently requires --sync-rounds 1")
    if max_steps != 1:
        errors.append("DiLoCo smoke currently requires --max-steps 1")
    if not errors:
        try:
            metrics = _run_one_round_diloco_shaped_protocol()
            runtime_checks.update(metrics)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"diloco_shaped_protocol_failed:{type(exc).__name__}")

    diloco_shape_passed = bool(metrics.get("diloco_shape_check_passed", False))
    syncer_passed = bool(metrics.get("syncer_role_check_passed", False))
    exchange_passed = bool(metrics.get("learner_syncer_exchange_completed", False))
    update_passed = bool(metrics.get("update_or_commit_check_passed", False))
    replay_passed = bool(metrics.get("replay_validated", False))
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = DilocoSmokeReport(
        diloco_smoke_status=(
            "passed"
            if (
                not errors
                and diloco_shape_passed
                and syncer_passed
                and exchange_passed
                and update_passed
                and replay_passed
            )
            else "failed"
        ),
        synthetic=synthetic,
        learners_requested=learners,
        sync_rounds_requested=sync_rounds,
        max_steps=max_steps,
        diloco_shape_check_passed=diloco_shape_passed,
        learner_count_observed=int(metrics.get("learner_count_observed", 0)),
        syncer_role_check_passed=syncer_passed,
        learner_syncer_exchange_check_passed=exchange_passed,
        update_or_commit_check_passed=update_passed,
        sync_rounds_completed=int(metrics.get("sync_rounds_completed", 0)),
        global_version_before=(
            int(metrics["global_version_before"])
            if "global_version_before" in metrics
            else None
        ),
        global_version_after=(
            int(metrics["global_version_after"])
            if "global_version_after" in metrics
            else None
        ),
        synthetic_updates_produced=int(metrics.get("synthetic_updates_produced", 0)),
        synthetic_updates_accepted=int(metrics.get("synthetic_updates_accepted", 0)),
        synthetic_updates_rejected=int(metrics.get("synthetic_updates_rejected", 0)),
        useful_synthetic_tokens=(
            int(metrics["useful_synthetic_tokens"])
            if "useful_synthetic_tokens" in metrics
            else None
        ),
        useful_synthetic_tokens_reason=None
        if "useful_synthetic_tokens" in metrics
        else "not meaningful because DiLoCo-shaped round did not complete",
        stale_update_count=(
            int(metrics["stale_update_count"]) if "stale_update_count" in metrics else None
        ),
        stale_update_count_reason=None
        if "stale_update_count" in metrics
        else "not meaningful because update stream did not complete",
        duplicate_update_count=(
            int(metrics["duplicate_update_count"])
            if "duplicate_update_count" in metrics
            else None
        ),
        duplicate_update_count_reason=None
        if "duplicate_update_count" in metrics
        else "not meaningful because update stream did not complete",
        replay_or_metric_check_passed=replay_passed,
        artifact_or_report_check_passed=False,
        optimization_fidelity="diloco_shaped_protocol_only",
        inner_optimizer_semantics="synthetic_placeholder",
        outer_optimizer_semantics="token_weighted_merge",
        parameter_fragment_semantics="not_exercised",
        runtime_checks=runtime_checks,
        modules_imported=[
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
            "decodilo.syncer.token_weighted_merge",
            "decodilo.syncer.outer_optimizer",
        ],
        skipped_checks={
            "full_diloco_optimizer_fidelity": (
                "not claimed; active path verifies DiLoCo-shaped learner/syncer "
                "protocol mechanics only"
            ),
            "inner_adamw": "not exercised by this synthetic no-training smoke",
            "outer_nesterov": (
                "not exercised; current safe local primitive uses token-weighted merge"
            ),
            "true_model_fragment": (
                "not exercised; synthetic numeric vector is used instead of model data"
            ),
            "real_training": "forbidden for DiLoCo smoke",
            "network": "forbidden for DiLoCo smoke",
            "gpu": "not required for DiLoCo smoke",
            "torch": "not required for DiLoCo smoke",
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
    loaded = load_diloco_smoke_report(target)
    artifact_report_passed = (
        loaded.diloco_smoke_status == report.diloco_smoke_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 32_768
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_diloco_smoke_report(path: str | Path) -> DilocoSmokeReport:
    return DilocoSmokeReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _run_one_round_diloco_shaped_protocol() -> dict[str, bool | int | float | str]:
    learner_id = "learner-0"
    round_id = "diloco-round-0"
    global_version_before = 0
    global_version_after = 1
    max_steps = 1
    useful_tokens = 21
    base_vector = np.asarray([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    synthetic_local_delta = np.asarray([0.125, -0.25, 0.375, -0.5], dtype=np.float64)
    learner_vector = base_vector + synthetic_local_delta
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

    async def update_delivery() -> dict[str, bool | int | float | str]:
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
        metrics = stream.metrics_dict()
        return {
            "update_stream_pre_commit_wait_pending": pre_commit_wait_pending,
            "update_ready_after_commit": update_ready is True,
            "global_update_broadcasts": int(metrics["global_update_broadcasts"]),
            "global_update_messages_sent": int(metrics["global_update_messages_sent"]),
            "global_update_acks": int(metrics["global_update_acks"]),
            "duplicate_update_count": int(metrics["duplicate_global_update_acks"]),
            "stale_update_count": len(stale),
            "learner_lag_zero": stream.learner_update_lag_current == {learner_id: 0},
        }

    update_metrics = asyncio.run(update_delivery())
    log = EventLog(path=None, run_id="diloco-smoke")
    log.append(
        EventType.LEARNER_STARTED,
        logical_time=0,
        learner_id=learner_id,
        payload={
            "learner_id": learner_id,
            "global_version_seen": global_version_before,
            "synthetic_local_steps": max_steps,
            "optimization_fidelity": "diloco_shaped_protocol_only",
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
            "synthetic_local_delta": synthetic_local_delta.tolist(),
            "inner_optimizer_semantics": "synthetic_placeholder",
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
            "outer_optimizer_semantics": "token_weighted_merge",
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
        raise AssertionError("DiLoCo smoke replay did not produce final vector")
    if not np.allclose(replay.final_global_vector, merge.new_global_vector):
        raise AssertionError("DiLoCo smoke replay final vector mismatch")
    return {
        **update_metrics,
        "diloco_shape_check_passed": (
            len(merge.included_learner_ids) == 1
            and merge.included_learner_ids == [learner_id]
            and replay.sync_rounds_committed == 1
            and replay.global_versions == [global_version_after]
        ),
        "learner_count_observed": len(merge.included_learner_ids),
        "syncer_role_check_passed": replay.sync_rounds_committed == 1,
        "learner_syncer_exchange_completed": replay.accepted_useful_tokens
        == useful_tokens,
        "update_or_commit_check_passed": (
            update_metrics["global_update_acks"] == 1
            and global_version_after == global_version_before + 1
        ),
        "replay_validated": replay.accepted_useful_tokens == useful_tokens,
        "sync_rounds_completed": replay.sync_rounds_committed,
        "global_version_before": global_version_before,
        "global_version_after": global_version_after,
        "synthetic_updates_produced": 1,
        "synthetic_updates_accepted": 1,
        "synthetic_updates_rejected": replay.rejected_update_count,
        "useful_synthetic_tokens": replay.accepted_useful_tokens,
        "event_log_event_count": len(log.events),
        "synthetic_local_steps_completed": max_steps,
        "final_global_vector_l2": float(np.linalg.norm(replay.final_global_vector)),
        "weighted_delta_l2": float(np.linalg.norm(merge.weighted_delta)),
        "token_weight_learner_0": float(merge.token_weights[learner_id]),
    }


def _with_stable_artifact_size(report: DilocoSmokeReport) -> DilocoSmokeReport:
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
    if first.startswith("DiLoCo smoke requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("DiLoCo smoke currently requires"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("diloco_shaped_protocol_failed:"):
        return (
            "diloco_shaped_protocol_check",
            "diloco_shaped_protocol_failed",
            first,
        )
    return "diloco_smoke", "diloco_smoke_failed", first
