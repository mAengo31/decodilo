"""Complete bounded local synthetic DiLoCo experiment command."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.integrated_diloco_smoke import (
    _run_integrated_optimizer_protocol_smoke,
)

BoundedDilocoExperimentStatus = Literal["passed", "failed"]
OptimizationFidelity = Literal[
    "bounded_synthetic_diloco_experiment",
    "partial_bounded_synthetic_diloco_experiment",
    "not_verified",
]
ParameterFragmentSemantics = Literal[
    "synthetic_vector_fragments",
    "true_model_fragment",
    "not_exercised",
]
SafetySemantics = Literal["not_exercised", "synthetic_placeholder", "implemented"]

FRAGMENT_IDS = ["fragment_0", "fragment_1"]
FRAGMENT_RANGES = [[0, 1], [2, 2]]
FRAGMENT_SHAPES = [[2], [1]]


class BoundedDilocoExperimentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    bounded_diloco_experiment_status: BoundedDilocoExperimentStatus
    command: str = "dev bounded-diloco-experiment"
    synthetic: bool
    learners_requested: int
    learners_observed: int = 0
    learner_count_observed: int = 0
    sync_rounds_requested: int
    sync_rounds_completed: int = 0
    fragments_requested: int
    fragments_observed: int = 0
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
    launch_ready: bool = False
    launch_allowed: bool = False

    learner_syncer_exchange_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    quorum_or_acceptance_check_passed: bool | None = None
    quorum_or_acceptance_check_reason: str | None = None
    synthetic_updates_produced: int = 0
    synthetic_updates_accepted: int = 0
    synthetic_updates_rejected: int = 0
    global_version_before: int | None = None
    global_version_after: int | None = None
    useful_synthetic_tokens: int | None = None
    useful_synthetic_tokens_reason: str | None = None
    stale_update_count: int | None = None
    stale_update_count_reason: str | None = None
    duplicate_update_count: int | None = None
    duplicate_update_count_reason: str | None = None

    optimization_fidelity: OptimizationFidelity
    inner_optimizer_semantics: Literal["adamw", "not_exercised"]
    outer_optimizer_semantics: Literal["nesterov", "not_exercised"]
    pseudo_gradient_check_passed: bool = False
    inner_adamw_check_passed: bool = False
    outer_nesterov_check_passed: bool = False
    optimizer_state_roundtrip_check_passed: bool = False
    reference_value_check_passed: bool = False
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

    parameter_fragment_semantics: ParameterFragmentSemantics
    fragment_count: int = 0
    fragment_ids: list[str] = Field(default_factory=list)
    fragment_ranges: list[list[int]] = Field(default_factory=list)
    fragment_shapes: list[list[int]] = Field(default_factory=list)
    fragment_schedule: list[dict[str, Any]] = Field(default_factory=list)
    full_vector_before: list[float] = Field(default_factory=list)
    full_vector_after: list[float] = Field(default_factory=list)
    reconstructed_vector_after: list[float] = Field(default_factory=list)
    fragment_versions_before: dict[str, int] = Field(default_factory=dict)
    fragment_versions_after: dict[str, int] = Field(default_factory=dict)
    fragment_state_roundtrip_check_passed: bool = False
    fragment_update_check_passed: bool = False
    fragment_merge_check_passed: bool = False
    fragment_reconstruction_check_passed: bool = False
    fragment_schedule_check_passed: bool = False
    per_fragment_reference_check_passed: bool = False
    global_reference_check_passed: bool = False

    protocol_optimizer_link_check_passed: bool = False
    optimizer_fragment_link_check_passed: bool = False
    protocol_fragment_link_check_passed: bool = False
    integrated_reference_check_passed: bool = False
    replay_or_metric_check_passed: bool | None = None
    artifact_or_report_check_passed: bool | None = None

    full_diloco_training_claimed: bool = False
    real_model_training_claimed: bool = False
    true_model_fragment_claimed: bool = False
    overlap_semantics: SafetySemantics = "not_exercised"
    quantization_semantics: SafetySemantics = "not_exercised"
    skipped_checks: dict[str, str] = Field(default_factory=dict)
    runtime_checks: dict[str, bool | int | float | str] = Field(default_factory=dict)
    modules_imported: list[str] = Field(default_factory=list)
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error_message: str | None = None
    artifact_bytes: int = 0
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_safety_and_claims(self) -> BoundedDilocoExperimentReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("bounded DiLoCo experiment report cannot enable launch")
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
            raise ValueError(
                "bounded DiLoCo experiment report cannot require unsafe behavior"
            )
        if (
            self.full_diloco_training_claimed
            or self.real_model_training_claimed
            or self.true_model_fragment_claimed
        ):
            raise ValueError("bounded experiment cannot claim unexercised training paths")
        if self.parameter_fragment_semantics == "true_model_fragment":
            raise ValueError("true model fragment semantics are not exercised here")
        if self.overlap_semantics != "not_exercised":
            raise ValueError("overlap semantics are not exercised by this command")
        if self.quantization_semantics != "not_exercised":
            raise ValueError("quantization semantics are not exercised by this command")
        if (
            self.bounded_diloco_experiment_status == "passed"
            and (
                self.optimization_fidelity != "bounded_synthetic_diloco_experiment"
                or self.inner_optimizer_semantics != "adamw"
                or self.outer_optimizer_semantics != "nesterov"
                or self.parameter_fragment_semantics
                != "synthetic_vector_fragments"
                or self.learners_observed != 1
                or self.sync_rounds_completed != 1
                or self.fragments_observed != 2
                or self.fragment_count != 2
                or not self.learner_syncer_exchange_check_passed
                or not self.update_or_commit_check_passed
                or not self.quorum_or_acceptance_check_passed
                or not self.pseudo_gradient_check_passed
                or not self.inner_adamw_check_passed
                or not self.outer_nesterov_check_passed
                or not self.optimizer_state_roundtrip_check_passed
                or not self.reference_value_check_passed
                or not self.fragment_state_roundtrip_check_passed
                or not self.fragment_update_check_passed
                or not self.fragment_merge_check_passed
                or not self.fragment_reconstruction_check_passed
                or not self.fragment_schedule_check_passed
                or not self.per_fragment_reference_check_passed
                or not self.global_reference_check_passed
                or not self.protocol_optimizer_link_check_passed
                or not self.optimizer_fragment_link_check_passed
                or not self.protocol_fragment_link_check_passed
                or not self.integrated_reference_check_passed
                or not self.replay_or_metric_check_passed
            )
        ):
            raise ValueError(
                "passing bounded experiment requires verified protocol, optimizer, "
                "fragment, and integration checks"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_bounded_diloco_experiment(
    *,
    synthetic: bool,
    learners: int,
    sync_rounds: int,
    fragments: int,
    inner_optimizer: str,
    outer_optimizer: str,
    max_steps: int,
    out: str | Path,
) -> BoundedDilocoExperimentReport:
    start = time.monotonic()
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    if not synthetic:
        errors.append("Bounded DiLoCo experiment requires --synthetic")
    if learners != 1:
        errors.append("Bounded DiLoCo experiment currently requires --learners 1")
    if sync_rounds != 1:
        errors.append("Bounded DiLoCo experiment currently requires --sync-rounds 1")
    if fragments != 2:
        errors.append("Bounded DiLoCo experiment currently requires --fragments 2")
    if inner_optimizer != "adamw":
        errors.append(
            "Bounded DiLoCo experiment currently requires --inner-optimizer adamw"
        )
    if outer_optimizer != "nesterov":
        errors.append(
            "Bounded DiLoCo experiment currently requires --outer-optimizer nesterov"
        )
    if max_steps != 1:
        errors.append("Bounded DiLoCo experiment currently requires --max-steps 1")

    if not errors:
        try:
            metrics = _run_bounded_reference_experiment()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"bounded_diloco_experiment_failed:{type(exc).__name__}")

    checks = _checks_from_metrics(metrics)
    all_checks_passed = not errors and all(checks.values())
    partial_checks_passed = not all_checks_passed and any(checks.values())
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = BoundedDilocoExperimentReport(
        bounded_diloco_experiment_status="passed" if all_checks_passed else "failed",
        synthetic=synthetic,
        learners_requested=learners,
        learners_observed=int(metrics.get("learners_observed", 0)),
        learner_count_observed=int(metrics.get("learners_observed", 0)),
        sync_rounds_requested=sync_rounds,
        sync_rounds_completed=int(metrics.get("sync_rounds_completed", 0)),
        fragments_requested=fragments,
        fragments_observed=int(metrics.get("fragments_observed", 0)),
        max_steps=max_steps,
        inner_optimizer_requested=inner_optimizer,
        outer_optimizer_requested=outer_optimizer,
        learner_syncer_exchange_check_passed=checks[
            "learner_syncer_exchange_check_passed"
        ],
        update_or_commit_check_passed=checks["update_or_commit_check_passed"],
        quorum_or_acceptance_check_passed=checks[
            "quorum_or_acceptance_check_passed"
        ],
        quorum_or_acceptance_check_reason=None
        if "quorum_or_acceptance_check_passed" in metrics
        else "not meaningful because bounded experiment did not complete",
        synthetic_updates_produced=int(metrics.get("synthetic_updates_produced", 0)),
        synthetic_updates_accepted=int(metrics.get("synthetic_updates_accepted", 0)),
        synthetic_updates_rejected=int(metrics.get("synthetic_updates_rejected", 0)),
        global_version_before=metrics.get("global_version_before"),
        global_version_after=metrics.get("global_version_after"),
        useful_synthetic_tokens=metrics.get("useful_synthetic_tokens"),
        useful_synthetic_tokens_reason=None
        if "useful_synthetic_tokens" in metrics
        else "not meaningful because bounded experiment did not complete",
        stale_update_count=metrics.get("stale_update_count"),
        stale_update_count_reason=None
        if "stale_update_count" in metrics
        else "not meaningful because update stream did not complete",
        duplicate_update_count=metrics.get("duplicate_update_count"),
        duplicate_update_count_reason=None
        if "duplicate_update_count" in metrics
        else "not meaningful because update stream did not complete",
        optimization_fidelity=(
            "bounded_synthetic_diloco_experiment"
            if all_checks_passed
            else (
                "partial_bounded_synthetic_diloco_experiment"
                if partial_checks_passed
                else "not_verified"
            )
        ),
        inner_optimizer_semantics="adamw"
        if checks["inner_adamw_check_passed"]
        else "not_exercised",
        outer_optimizer_semantics="nesterov"
        if checks["outer_nesterov_check_passed"]
        else "not_exercised",
        pseudo_gradient_check_passed=checks["pseudo_gradient_check_passed"],
        inner_adamw_check_passed=checks["inner_adamw_check_passed"],
        outer_nesterov_check_passed=checks["outer_nesterov_check_passed"],
        optimizer_state_roundtrip_check_passed=checks[
            "optimizer_state_roundtrip_check_passed"
        ],
        reference_value_check_passed=checks["reference_value_check_passed"],
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
        parameter_fragment_semantics=(
            "synthetic_vector_fragments"
            if all_checks_passed
            else "not_exercised"
        ),
        fragment_count=int(metrics.get("fragment_count", 0)),
        fragment_ids=list(metrics.get("fragment_ids", [])),
        fragment_ranges=list(metrics.get("fragment_ranges", [])),
        fragment_shapes=list(metrics.get("fragment_shapes", [])),
        fragment_schedule=list(metrics.get("fragment_schedule", [])),
        full_vector_before=list(metrics.get("full_vector_before", [])),
        full_vector_after=list(metrics.get("full_vector_after", [])),
        reconstructed_vector_after=list(metrics.get("reconstructed_vector_after", [])),
        fragment_versions_before=dict(metrics.get("fragment_versions_before", {})),
        fragment_versions_after=dict(metrics.get("fragment_versions_after", {})),
        fragment_state_roundtrip_check_passed=checks[
            "fragment_state_roundtrip_check_passed"
        ],
        fragment_update_check_passed=checks["fragment_update_check_passed"],
        fragment_merge_check_passed=checks["fragment_merge_check_passed"],
        fragment_reconstruction_check_passed=checks[
            "fragment_reconstruction_check_passed"
        ],
        fragment_schedule_check_passed=checks["fragment_schedule_check_passed"],
        per_fragment_reference_check_passed=checks[
            "per_fragment_reference_check_passed"
        ],
        global_reference_check_passed=checks["global_reference_check_passed"],
        protocol_optimizer_link_check_passed=checks[
            "protocol_optimizer_link_check_passed"
        ],
        optimizer_fragment_link_check_passed=checks[
            "optimizer_fragment_link_check_passed"
        ],
        protocol_fragment_link_check_passed=checks[
            "protocol_fragment_link_check_passed"
        ],
        integrated_reference_check_passed=checks["integrated_reference_check_passed"],
        replay_or_metric_check_passed=checks["replay_or_metric_check_passed"],
        artifact_or_report_check_passed=False,
        skipped_checks={
            "full_diloco_training": (
                "not claimed; this is a bounded synthetic experiment over tiny "
                "deterministic vectors"
            ),
            "true_model_fragment": (
                "not claimed; fragments are deterministic synthetic vector fragments"
            ),
            "communication_overlap": (
                "not exercised; no communication/computation overlap is modeled"
            ),
            "quantized_communication": (
                "not exercised; fragment values remain plain float vectors"
            ),
            "real_model_training": "forbidden for bounded synthetic experiment",
            "network": "forbidden for bounded synthetic experiment",
            "package_install": "forbidden for local command execution",
            "gpu": "not required for bounded synthetic experiment",
            "torch": "not required for bounded synthetic experiment",
        },
        runtime_checks={
            key: value
            for key, value in metrics.items()
            if isinstance(value, bool | int | float | str)
        },
        modules_imported=[
            "decodilo.dev.integrated_diloco_smoke",
            "decodilo.runtime.update_stream",
            "decodilo.syncer.event_log",
            "decodilo.syncer.replay",
            "decodilo.syncer.token_weighted_merge",
            "decodilo.syncer.outer_optimizer",
        ],
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
    loaded = load_bounded_diloco_experiment_report(target)
    artifact_report_passed = (
        loaded.bounded_diloco_experiment_status
        == report.bounded_diloco_experiment_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 32_768
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_bounded_diloco_experiment_report(
    path: str | Path,
) -> BoundedDilocoExperimentReport:
    return BoundedDilocoExperimentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_bounded_reference_experiment() -> dict[str, Any]:
    tolerance = 1e-12
    core = _run_integrated_optimizer_protocol_smoke()
    initial_parameters = list(core["initial_parameters"])
    post_inner_parameters = list(core["post_inner_parameters"])
    pseudo_gradient = list(core["pseudo_gradient"])
    fragments_before = {
        "fragment_0": initial_parameters[0:2],
        "fragment_1": initial_parameters[2:3],
    }
    fragments_after = {
        "fragment_0": post_inner_parameters[0:2],
        "fragment_1": post_inner_parameters[2:3],
    }
    fragment_updates = {
        fragment_id: [
            after - before
            for before, after in zip(
                fragments_before[fragment_id],
                fragments_after[fragment_id],
                strict=True,
            )
        ]
        for fragment_id in FRAGMENT_IDS
    }
    fragment_schedule = [
        {
            "step": 1,
            "fragment_id": "fragment_0",
            "range": [0, 1],
            "update": fragment_updates["fragment_0"],
        },
        {
            "step": 1,
            "fragment_id": "fragment_1",
            "range": [2, 2],
            "update": fragment_updates["fragment_1"],
        },
    ]
    reconstructed_vector_after = [
        *fragments_after["fragment_0"],
        *fragments_after["fragment_1"],
    ]
    versions_before = {"fragment_0": 0, "fragment_1": 0}
    versions_after = {"fragment_0": 1, "fragment_1": 1}
    state = {
        "fragment_ids": list(FRAGMENT_IDS),
        "fragment_ranges": list(FRAGMENT_RANGES),
        "fragment_shapes": list(FRAGMENT_SHAPES),
        "fragment_versions": versions_after,
        "fragments": fragments_after,
        "schedule": fragment_schedule,
    }
    state_roundtrip = json.loads(json.dumps(state, sort_keys=True))
    fragment_reconstruction_error = _max_abs_delta(
        reconstructed_vector_after,
        post_inner_parameters,
    )
    pseudo_gradient_from_fragments = [
        before - after
        for before, after in zip(
            initial_parameters,
            reconstructed_vector_after,
            strict=True,
        )
    ]
    fragment_pseudo_gradient_error = _max_abs_delta(
        pseudo_gradient_from_fragments,
        pseudo_gradient,
    )
    protocol_fragment_error = _max_abs_delta(
        list(core["protocol_committed_parameters"]),
        reconstructed_vector_after,
    )
    max_abs_error = max(
        float(core["max_abs_error"]),
        fragment_reconstruction_error,
        fragment_pseudo_gradient_error,
        protocol_fragment_error,
    )
    fragment_update_check_passed = all(
        _float_lists_close(
            [
                before + delta
                for before, delta in zip(
                    fragments_before[fragment_id],
                    fragment_updates[fragment_id],
                    strict=True,
                )
            ],
            fragments_after[fragment_id],
            tolerance,
        )
        for fragment_id in FRAGMENT_IDS
    )
    fragment_schedule_check_passed = (
        len(fragment_schedule) == 2
        and [entry["fragment_id"] for entry in fragment_schedule] == FRAGMENT_IDS
        and [entry["range"] for entry in fragment_schedule] == FRAGMENT_RANGES
    )
    per_fragment_reference_check_passed = all(
        _float_lists_close(
            fragments_after[fragment_id],
            post_inner_parameters[start : stop + 1],
            tolerance,
        )
        for fragment_id, (start, stop) in zip(
            FRAGMENT_IDS,
            FRAGMENT_RANGES,
            strict=True,
        )
    )
    fragment_checks = {
        "fragments_observed": 2,
        "fragment_count": 2,
        "fragment_ids": list(FRAGMENT_IDS),
        "fragment_ranges": list(FRAGMENT_RANGES),
        "fragment_shapes": list(FRAGMENT_SHAPES),
        "fragment_schedule": fragment_schedule,
        "full_vector_before": initial_parameters,
        "full_vector_after": post_inner_parameters,
        "reconstructed_vector_after": reconstructed_vector_after,
        "fragment_versions_before": versions_before,
        "fragment_versions_after": versions_after,
        "fragment_state_roundtrip_check_passed": state_roundtrip == state,
        "fragment_update_check_passed": fragment_update_check_passed,
        "fragment_merge_check_passed": reconstructed_vector_after
        == [
            *fragments_after["fragment_0"],
            *fragments_after["fragment_1"],
        ],
        "fragment_reconstruction_check_passed": fragment_reconstruction_error
        <= tolerance,
        "fragment_schedule_check_passed": fragment_schedule_check_passed,
        "per_fragment_reference_check_passed": per_fragment_reference_check_passed,
        "global_reference_check_passed": max_abs_error <= tolerance,
        "optimizer_fragment_link_check_passed": fragment_pseudo_gradient_error
        <= tolerance,
        "protocol_fragment_link_check_passed": protocol_fragment_error <= tolerance,
    }
    integrated_reference_check_passed = (
        bool(core["learner_syncer_exchange_check_passed"])
        and bool(core["update_or_commit_check_passed"])
        and bool(core["replay_or_metric_check_passed"])
        and bool(core["pseudo_gradient_check_passed"])
        and bool(core["inner_adamw_check_passed"])
        and bool(core["outer_nesterov_check_passed"])
        and bool(core["optimizer_state_roundtrip_check_passed"])
        and bool(core["reference_value_check_passed"])
        and bool(core["protocol_optimizer_link_check_passed"])
        and all(
            bool(fragment_checks[key])
            for key in [
                "fragment_state_roundtrip_check_passed",
                "fragment_update_check_passed",
                "fragment_merge_check_passed",
                "fragment_reconstruction_check_passed",
                "fragment_schedule_check_passed",
                "per_fragment_reference_check_passed",
                "global_reference_check_passed",
                "optimizer_fragment_link_check_passed",
                "protocol_fragment_link_check_passed",
            ]
        )
    )
    return {
        **core,
        **fragment_checks,
        "learners_observed": int(core["learner_count_observed"]),
        "quorum_or_acceptance_check_passed": (
            int(core["synthetic_updates_produced"]) == 1
            and int(core["synthetic_updates_accepted"]) == 1
            and int(core["synthetic_updates_rejected"]) == 0
        ),
        "integrated_reference_check_passed": integrated_reference_check_passed,
        "max_abs_error": max_abs_error,
    }


def _checks_from_metrics(metrics: dict[str, Any]) -> dict[str, bool]:
    keys = [
        "learner_syncer_exchange_check_passed",
        "update_or_commit_check_passed",
        "quorum_or_acceptance_check_passed",
        "pseudo_gradient_check_passed",
        "inner_adamw_check_passed",
        "outer_nesterov_check_passed",
        "optimizer_state_roundtrip_check_passed",
        "reference_value_check_passed",
        "fragment_state_roundtrip_check_passed",
        "fragment_update_check_passed",
        "fragment_merge_check_passed",
        "fragment_reconstruction_check_passed",
        "fragment_schedule_check_passed",
        "per_fragment_reference_check_passed",
        "global_reference_check_passed",
        "protocol_optimizer_link_check_passed",
        "optimizer_fragment_link_check_passed",
        "protocol_fragment_link_check_passed",
        "integrated_reference_check_passed",
        "replay_or_metric_check_passed",
    ]
    return {key: bool(metrics.get(key, False)) for key in keys}


def _with_stable_artifact_size(
    report: BoundedDilocoExperimentReport,
) -> BoundedDilocoExperimentReport:
    size = 0
    for _ in range(8):
        candidate = report.model_copy(update={"artifact_bytes": size})
        next_size = len(candidate.to_json().encode("utf-8"))
        if next_size == size:
            return candidate
        size = next_size
    return report.model_copy(update={"artifact_bytes": size})


def _classify_failure(errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not errors:
        return None, None, None
    if any("requires" in error for error in errors):
        return (
            "argument_validation",
            "invalid_arguments",
            "Bounded DiLoCo experiment rejected unsupported bounded arguments.",
        )
    return (
        "bounded_diloco_experiment_execution",
        "execution_error",
        "Bounded DiLoCo experiment failed during local deterministic execution.",
    )


def _max_abs_delta(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return float("inf")
    return max((abs(a - b) for a, b in zip(left, right, strict=True)), default=0.0)


def _float_lists_close(left: list[float], right: list[float], tolerance: float) -> bool:
    return _max_abs_delta(left, right) <= tolerance
