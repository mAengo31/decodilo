"""Bounded local parameter-fragment synthetic smoke command."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ParameterFragmentSmokeStatus = Literal["passed", "failed"]
ParameterFragmentSemantics = Literal[
    "synthetic_vector_fragments",
    "true_model_fragment",
    "storage_chunk_only",
    "not_exercised",
]
FragmentScheduleType = Literal["sequential", "explicit", "synthetic_placeholder"]
SafetySemantics = Literal["not_exercised", "synthetic_placeholder", "implemented"]

INITIAL_VECTOR = [1.0, 2.0, 3.0, 4.0]
FRAGMENT_IDS = ["fragment_0", "fragment_1"]
FRAGMENT_RANGES = [[0, 1], [2, 3]]
FRAGMENT_SHAPES = [[2], [2]]
FRAGMENT_UPDATE_ID = "fragment_1"
FRAGMENT_UPDATE = [0.25, -0.5]
EXPECTED_VECTOR_AFTER = [1.0, 2.0, 3.25, 3.5]


class ParameterFragmentSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    parameter_fragment_smoke_status: ParameterFragmentSmokeStatus
    command: str = "dev parameter-fragment-smoke"
    synthetic: bool
    fragments_requested: int
    fragments_observed: int
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    real_model_training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    parameter_fragment_semantics: ParameterFragmentSemantics
    fragment_schedule_type: FragmentScheduleType
    fragment_count: int
    fragment_ids: list[str] = Field(default_factory=list)
    fragment_ranges: list[list[int]] = Field(default_factory=list)
    fragment_shapes: list[list[int]] = Field(default_factory=list)
    fragment_schedule: list[dict[str, Any]] = Field(default_factory=list)
    full_vector_before: list[float] = Field(default_factory=list)
    full_vector_after: list[float] = Field(default_factory=list)
    reconstructed_vector_after: list[float] = Field(default_factory=list)
    expected_vector_after: list[float] = Field(default_factory=list)
    fragment_versions_before: dict[str, int] = Field(default_factory=dict)
    fragment_versions_after: dict[str, int] = Field(default_factory=dict)
    fragment_state_roundtrip_check_passed: bool = False
    fragment_update_check_passed: bool = False
    fragment_merge_check_passed: bool = False
    fragment_reconstruction_check_passed: bool = False
    fragment_schedule_check_passed: bool = False
    per_fragment_reference_check_passed: bool = False
    global_reference_check_passed: bool = False
    tolerance: float = 1e-12
    max_abs_error: float | None = None
    overlap_semantics: SafetySemantics = "not_exercised"
    quantization_semantics: SafetySemantics = "not_exercised"
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
    def _validate_disabled(self) -> ParameterFragmentSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("parameter-fragment smoke report cannot enable launch")
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
                "parameter-fragment smoke report cannot require unsafe behavior"
            )
        if self.parameter_fragment_semantics == "true_model_fragment":
            raise ValueError("true model fragment semantics are not exercised here")
        if (
            self.parameter_fragment_smoke_status == "passed"
            and (
                self.parameter_fragment_semantics != "synthetic_vector_fragments"
                or self.fragment_count != 2
                or self.fragments_observed != 2
                or not self.fragment_state_roundtrip_check_passed
                or not self.fragment_update_check_passed
                or not self.fragment_merge_check_passed
                or not self.fragment_reconstruction_check_passed
                or not self.fragment_schedule_check_passed
                or not self.per_fragment_reference_check_passed
                or not self.global_reference_check_passed
            )
        ):
            raise ValueError(
                "passing parameter-fragment smoke requires verified synthetic fragments"
            )
        if self.overlap_semantics != "not_exercised":
            raise ValueError("overlap semantics are not exercised by this smoke")
        if self.quantization_semantics != "not_exercised":
            raise ValueError("quantization semantics are not exercised by this smoke")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_parameter_fragment_smoke(
    *,
    synthetic: bool,
    fragments: int,
    max_steps: int,
    out: str | Path,
) -> ParameterFragmentSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    if not synthetic:
        errors.append("Parameter-fragment smoke requires --synthetic")
    if fragments != 2:
        errors.append("Parameter-fragment smoke currently requires --fragments 2")
    if max_steps != 1:
        errors.append("Parameter-fragment smoke currently requires --max-steps 1")

    if not errors:
        try:
            metrics = _run_reference_parameter_fragment_smoke()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"parameter_fragment_reference_failed:{type(exc).__name__}")

    checks = {
        "fragment_state_roundtrip_check_passed": bool(
            metrics.get("fragment_state_roundtrip_check_passed", False)
        ),
        "fragment_update_check_passed": bool(
            metrics.get("fragment_update_check_passed", False)
        ),
        "fragment_merge_check_passed": bool(
            metrics.get("fragment_merge_check_passed", False)
        ),
        "fragment_reconstruction_check_passed": bool(
            metrics.get("fragment_reconstruction_check_passed", False)
        ),
        "fragment_schedule_check_passed": bool(
            metrics.get("fragment_schedule_check_passed", False)
        ),
        "per_fragment_reference_check_passed": bool(
            metrics.get("per_fragment_reference_check_passed", False)
        ),
        "global_reference_check_passed": bool(
            metrics.get("global_reference_check_passed", False)
        ),
    }
    all_checks_passed = not errors and all(checks.values())
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = ParameterFragmentSmokeReport(
        parameter_fragment_smoke_status="passed" if all_checks_passed else "failed",
        synthetic=synthetic,
        fragments_requested=fragments,
        fragments_observed=int(metrics.get("fragments_observed", 0)),
        max_steps=max_steps,
        parameter_fragment_semantics=(
            "synthetic_vector_fragments" if all_checks_passed else "not_exercised"
        ),
        fragment_schedule_type=(
            "explicit"
            if metrics.get("fragment_schedule_check_passed")
            else "synthetic_placeholder"
        ),
        fragment_count=int(metrics.get("fragment_count", 0)),
        fragment_ids=list(metrics.get("fragment_ids", [])),
        fragment_ranges=list(metrics.get("fragment_ranges", [])),
        fragment_shapes=list(metrics.get("fragment_shapes", [])),
        fragment_schedule=list(metrics.get("fragment_schedule", [])),
        full_vector_before=list(metrics.get("full_vector_before", [])),
        full_vector_after=list(metrics.get("full_vector_after", [])),
        reconstructed_vector_after=list(metrics.get("reconstructed_vector_after", [])),
        expected_vector_after=list(metrics.get("expected_vector_after", [])),
        fragment_versions_before=dict(metrics.get("fragment_versions_before", {})),
        fragment_versions_after=dict(metrics.get("fragment_versions_after", {})),
        **checks,
        tolerance=1e-12,
        max_abs_error=metrics.get("max_abs_error"),
        skipped_checks={
            "true_model_fragment": (
                "not exercised; this smoke uses deterministic synthetic vector "
                "fragments only"
            ),
            "communication_overlap": (
                "not exercised; no communication/computation overlap is modeled"
            ),
            "quantized_communication": (
                "not exercised; fragment values remain plain float vectors"
            ),
            "full_streaming_diloco": "not claimed by this bounded fragment smoke",
            "real_model_training": "forbidden for parameter-fragment smoke",
            "network": "forbidden for parameter-fragment smoke",
            "gpu": "not required for parameter-fragment smoke",
            "torch": "not required for parameter-fragment smoke",
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
    loaded = load_parameter_fragment_smoke_report(target)
    final_report = _with_stable_artifact_size(loaded)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_parameter_fragment_smoke_report(
    path: str | Path,
) -> ParameterFragmentSmokeReport:
    return ParameterFragmentSmokeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_reference_parameter_fragment_smoke() -> dict[str, Any]:
    tolerance = 1e-12
    full_vector_before = list(INITIAL_VECTOR)
    fragments_before = {
        "fragment_0": full_vector_before[0:2],
        "fragment_1": full_vector_before[2:4],
    }
    versions_before = {"fragment_0": 0, "fragment_1": 0}
    fragment_schedule = [
        {
            "step": 1,
            "fragment_id": FRAGMENT_UPDATE_ID,
            "range": [2, 3],
            "update": list(FRAGMENT_UPDATE),
        }
    ]
    fragments_after = {key: list(value) for key, value in fragments_before.items()}
    fragments_after[FRAGMENT_UPDATE_ID] = [
        value + delta
        for value, delta in zip(
            fragments_after[FRAGMENT_UPDATE_ID],
            FRAGMENT_UPDATE,
            strict=True,
        )
    ]
    versions_after = dict(versions_before)
    versions_after[FRAGMENT_UPDATE_ID] += 1
    reconstructed_vector_after = [
        *fragments_after["fragment_0"],
        *fragments_after["fragment_1"],
    ]
    max_abs_error = _max_abs_delta(reconstructed_vector_after, EXPECTED_VECTOR_AFTER)
    state = {
        "fragment_ids": list(FRAGMENT_IDS),
        "fragment_ranges": list(FRAGMENT_RANGES),
        "fragment_shapes": list(FRAGMENT_SHAPES),
        "fragment_versions": versions_after,
        "fragments": fragments_after,
        "schedule": fragment_schedule,
    }
    state_roundtrip = json.loads(json.dumps(state, sort_keys=True))
    fragment_update_check = fragments_after["fragment_1"] == [3.25, 3.5]
    fragment_merge_check = reconstructed_vector_after == [
        *fragments_after["fragment_0"],
        *fragments_after["fragment_1"],
    ]
    fragment_reconstruction_check = _float_lists_close(
        reconstructed_vector_after,
        EXPECTED_VECTOR_AFTER,
        tolerance,
    )
    fragment_schedule_check = (
        len(fragment_schedule) == 1
        and fragment_schedule[0]["fragment_id"] == "fragment_1"
        and fragment_schedule[0]["range"] == [2, 3]
    )
    per_fragment_reference_check = (
        fragments_after["fragment_0"] == [1.0, 2.0]
        and _float_lists_close(fragments_after["fragment_1"], [3.25, 3.5], tolerance)
        and versions_after == {"fragment_0": 0, "fragment_1": 1}
    )
    global_reference_check = max_abs_error <= tolerance
    return {
        "fragments_observed": 2,
        "fragment_count": 2,
        "fragment_ids": list(FRAGMENT_IDS),
        "fragment_ranges": list(FRAGMENT_RANGES),
        "fragment_shapes": list(FRAGMENT_SHAPES),
        "fragment_schedule": fragment_schedule,
        "full_vector_before": full_vector_before,
        "full_vector_after": list(EXPECTED_VECTOR_AFTER),
        "reconstructed_vector_after": reconstructed_vector_after,
        "expected_vector_after": list(EXPECTED_VECTOR_AFTER),
        "fragment_versions_before": versions_before,
        "fragment_versions_after": versions_after,
        "fragment_state_roundtrip_check_passed": state_roundtrip == state,
        "fragment_update_check_passed": fragment_update_check,
        "fragment_merge_check_passed": fragment_merge_check,
        "fragment_reconstruction_check_passed": fragment_reconstruction_check,
        "fragment_schedule_check_passed": fragment_schedule_check,
        "per_fragment_reference_check_passed": per_fragment_reference_check,
        "global_reference_check_passed": global_reference_check,
        "max_abs_error": max_abs_error,
    }


def _classify_failure(errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not errors:
        return None, None, None
    if any("requires" in error for error in errors):
        return (
            "argument_validation",
            "invalid_arguments",
            "Parameter-fragment smoke rejected unsupported bounded arguments.",
        )
    return (
        "parameter_fragment_smoke_execution",
        "execution_error",
        "Parameter-fragment smoke failed during local deterministic execution.",
    )


def _with_stable_artifact_size(
    report: ParameterFragmentSmokeReport,
) -> ParameterFragmentSmokeReport:
    size = 0
    for _ in range(8):
        candidate = report.model_copy(update={"artifact_bytes": size})
        next_size = len(candidate.to_json().encode("utf-8"))
        if next_size == size:
            return candidate
        size = next_size
    return report.model_copy(update={"artifact_bytes": size})


def _max_abs_delta(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return float("inf")
    return max((abs(a - b) for a, b in zip(left, right, strict=True)), default=0.0)


def _float_lists_close(left: list[float], right: list[float], tolerance: float) -> bool:
    return _max_abs_delta(left, right) <= tolerance
