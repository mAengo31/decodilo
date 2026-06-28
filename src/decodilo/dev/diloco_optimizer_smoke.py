"""Bounded local DiLoCo optimizer-fidelity smoke command."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DilocoOptimizerSmokeStatus = Literal["passed", "failed"]
OptimizationFidelity = Literal[
    "optimizer_semantics_smoke",
    "partial_optimizer_semantics_smoke",
    "not_verified",
]
InnerOptimizerSemantics = Literal["adamw", "not_exercised"]
OuterOptimizerSemantics = Literal["nesterov", "not_exercised"]
ParameterFragmentSemantics = Literal["not_exercised", "true_model_fragment"]


INITIAL_PARAMETERS = [1.0, -2.0, 0.5]
SYNTHETIC_GRADIENT = [0.1, -0.2, 0.05]
EXPECTED_POST_INNER_PARAMETERS = [
    0.9899000009999999,
    -1.9898000005,
    0.4899500019999996,
]
EXPECTED_PSEUDO_GRADIENT = [
    0.010099999000000137,
    -0.010199999499999945,
    0.010049998000000393,
]
EXPECTED_POST_OUTER_PARAMETERS = [
    0.9904050009499998,
    -1.990310000475,
    0.4904525018999996,
]


class DilocoOptimizerSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    diloco_optimizer_smoke_status: DilocoOptimizerSmokeStatus
    command: str = "dev diloco-optimizer-smoke"
    synthetic: bool
    max_steps: int
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    training_attempted: bool = False
    real_model_training_attempted: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    inner_optimizer_requested: str
    outer_optimizer_requested: str
    inner_optimizer_semantics: InnerOptimizerSemantics
    outer_optimizer_semantics: OuterOptimizerSemantics
    optimization_fidelity: OptimizationFidelity
    parameter_fragment_semantics: ParameterFragmentSemantics = "not_exercised"
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
    inner_hyperparameters: dict[str, float] = Field(default_factory=dict)
    outer_hyperparameters: dict[str, float] = Field(default_factory=dict)
    optimizer_state_roundtrip: dict[str, Any] = Field(default_factory=dict)
    pseudo_gradient_convention: str | None = None
    skipped_checks: dict[str, str] = Field(default_factory=dict)
    failed_check: str | None = None
    error_classification: str | None = None
    safe_error_message: str | None = None
    artifact_or_report_check_passed: bool | None = None
    artifact_bytes: int = 0
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> DilocoOptimizerSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("DiLoCo optimizer smoke report cannot enable launch")
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
            raise ValueError("DiLoCo optimizer smoke report cannot require unsafe behavior")
        if (
            self.optimization_fidelity == "optimizer_semantics_smoke"
            and (
                self.inner_optimizer_semantics != "adamw"
                or self.outer_optimizer_semantics != "nesterov"
                or not self.inner_adamw_check_passed
                or not self.outer_nesterov_check_passed
                or not self.pseudo_gradient_check_passed
                or not self.optimizer_state_roundtrip_check_passed
                or not self.reference_value_check_passed
            )
        ):
            raise ValueError("optimizer semantics smoke requires all optimizer checks")
        if self.parameter_fragment_semantics == "true_model_fragment":
            raise ValueError("true model fragment semantics are not exercised here")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_diloco_optimizer_smoke(
    *,
    synthetic: bool,
    inner_optimizer: str,
    outer_optimizer: str,
    max_steps: int,
    out: str | Path,
) -> DilocoOptimizerSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    if not synthetic:
        errors.append("DiLoCo optimizer smoke requires --synthetic")
    if inner_optimizer != "adamw":
        errors.append("DiLoCo optimizer smoke currently requires --inner-optimizer adamw")
    if outer_optimizer != "nesterov":
        errors.append("DiLoCo optimizer smoke currently requires --outer-optimizer nesterov")
    if max_steps != 1:
        errors.append("DiLoCo optimizer smoke currently requires --max-steps 1")

    metrics: dict[str, Any] = {}
    if not errors:
        try:
            metrics = _run_reference_optimizer_smoke()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"diloco_optimizer_reference_failed:{type(exc).__name__}")

    pseudo_passed = bool(metrics.get("pseudo_gradient_check_passed", False))
    inner_passed = bool(metrics.get("inner_adamw_check_passed", False))
    outer_passed = bool(metrics.get("outer_nesterov_check_passed", False))
    roundtrip_passed = bool(metrics.get("optimizer_state_roundtrip_check_passed", False))
    reference_passed = bool(metrics.get("reference_value_check_passed", False))
    all_checks_passed = (
        not errors
        and pseudo_passed
        and inner_passed
        and outer_passed
        and roundtrip_passed
        and reference_passed
    )
    partial_checks_passed = (
        not all_checks_passed
        and any(
            [
                pseudo_passed,
                inner_passed,
                outer_passed,
                roundtrip_passed,
                reference_passed,
            ]
        )
    )
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = DilocoOptimizerSmokeReport(
        diloco_optimizer_smoke_status="passed" if all_checks_passed else "failed",
        synthetic=synthetic,
        max_steps=max_steps,
        inner_optimizer_requested=inner_optimizer,
        outer_optimizer_requested=outer_optimizer,
        inner_optimizer_semantics="adamw" if inner_passed else "not_exercised",
        outer_optimizer_semantics="nesterov" if outer_passed else "not_exercised",
        optimization_fidelity=(
            "optimizer_semantics_smoke"
            if all_checks_passed
            else (
                "partial_optimizer_semantics_smoke"
                if partial_checks_passed
                else "not_verified"
            )
        ),
        pseudo_gradient_check_passed=pseudo_passed,
        inner_adamw_check_passed=inner_passed,
        outer_nesterov_check_passed=outer_passed,
        optimizer_state_roundtrip_check_passed=roundtrip_passed,
        reference_value_check_passed=reference_passed,
        max_abs_error=metrics.get("max_abs_error"),
        initial_parameters=list(metrics.get("initial_parameters", [])),
        synthetic_gradient=list(metrics.get("synthetic_gradient", [])),
        post_inner_parameters=list(metrics.get("post_inner_parameters", [])),
        pseudo_gradient=list(metrics.get("pseudo_gradient", [])),
        post_outer_parameters=list(metrics.get("post_outer_parameters", [])),
        expected_post_outer_parameters=list(
            metrics.get("expected_post_outer_parameters", [])
        ),
        inner_hyperparameters=dict(metrics.get("inner_hyperparameters", {})),
        outer_hyperparameters=dict(metrics.get("outer_hyperparameters", {})),
        optimizer_state_roundtrip=dict(metrics.get("optimizer_state_roundtrip", {})),
        pseudo_gradient_convention=metrics.get("pseudo_gradient_convention"),
        skipped_checks={
            "full_diloco_training": (
                "not claimed; this smoke verifies optimizer semantics over tiny "
                "synthetic vectors only"
            ),
            "real_model_training": "forbidden for optimizer smoke",
            "parameter_fragment_semantics": (
                "not exercised; no model or tensor-fragment synchronization is used"
            ),
            "network": "forbidden for optimizer smoke",
            "gpu": "not required for optimizer smoke",
            "torch": "not required for optimizer smoke",
        },
        failed_check=failed_check,
        error_classification=error_classification,
        safe_error_message=safe_error_message,
        artifact_or_report_check_passed=False,
        elapsed_seconds=max(0.0, time.monotonic() - start),
        errors=errors,
    )
    report = _with_stable_artifact_size(report)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
    loaded = load_diloco_optimizer_smoke_report(target)
    artifact_report_passed = (
        loaded.diloco_optimizer_smoke_status == report.diloco_optimizer_smoke_status
        and loaded.artifact_bytes == target.stat().st_size
        and target.stat().st_size < 32_768
    )
    final_report = report.model_copy(
        update={"artifact_or_report_check_passed": artifact_report_passed}
    )
    final_report = _with_stable_artifact_size(final_report)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_diloco_optimizer_smoke_report(path: str | Path) -> DilocoOptimizerSmokeReport:
    return DilocoOptimizerSmokeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_reference_optimizer_smoke() -> dict[str, Any]:
    tolerance = 1e-12
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
    inner_error = _max_abs_delta(post_inner, EXPECTED_POST_INNER_PARAMETERS)
    pseudo_error = _max_abs_delta(pseudo_gradient, EXPECTED_PSEUDO_GRADIENT)
    outer_error = _max_abs_delta(post_outer, EXPECTED_POST_OUTER_PARAMETERS)
    max_abs_error = max(inner_error, pseudo_error, outer_error)
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
        "initial_parameters": INITIAL_PARAMETERS,
        "synthetic_gradient": SYNTHETIC_GRADIENT,
        "post_inner_parameters": post_inner,
        "pseudo_gradient": pseudo_gradient,
        "post_outer_parameters": post_outer,
        "expected_post_outer_parameters": EXPECTED_POST_OUTER_PARAMETERS,
        "inner_hyperparameters": inner_hyperparameters,
        "outer_hyperparameters": outer_hyperparameters,
        "optimizer_state_roundtrip": optimizer_state_roundtrip,
        "pseudo_gradient_convention": (
            "pseudo_gradient = initial_parameters - post_inner_parameters"
        ),
        "inner_adamw_check_passed": inner_error <= tolerance,
        "pseudo_gradient_check_passed": pseudo_error <= tolerance,
        "outer_nesterov_check_passed": outer_error <= tolerance,
        "optimizer_state_roundtrip_check_passed": roundtrip_passed,
        "reference_value_check_passed": max_abs_error <= tolerance and roundtrip_passed,
        "max_abs_error": max_abs_error,
    }


def _adamw_reference_step(
    *,
    parameters: list[float],
    gradient: list[float],
    state: dict[str, Any],
    learning_rate: float,
    beta1: float,
    beta2: float,
    epsilon: float,
    weight_decay: float,
) -> tuple[list[float], dict[str, Any]]:
    step = int(state["step"]) + 1
    next_m: list[float] = []
    next_v: list[float] = []
    next_parameters: list[float] = []
    for index, value in enumerate(parameters):
        grad = gradient[index]
        m_t = beta1 * state["m"][index] + (1.0 - beta1) * grad
        v_t = beta2 * state["v"][index] + (1.0 - beta2) * grad * grad
        m_hat = m_t / (1.0 - beta1**step)
        v_hat = v_t / (1.0 - beta2**step)
        decayed = value * (1.0 - learning_rate * weight_decay)
        next_value = decayed - learning_rate * m_hat / (math.sqrt(v_hat) + epsilon)
        next_m.append(m_t)
        next_v.append(v_t)
        next_parameters.append(next_value)
    return next_parameters, {"step": step, "m": next_m, "v": next_v}


def _nesterov_reference_step(
    *,
    parameters: list[float],
    pseudo_gradient: list[float],
    state: dict[str, Any],
    learning_rate: float,
    momentum: float,
) -> tuple[list[float], dict[str, Any]]:
    step = int(state["step"]) + 1
    velocity: list[float] = []
    post_outer: list[float] = []
    for index, value in enumerate(parameters):
        updated_velocity = momentum * state["velocity"][index] + pseudo_gradient[index]
        nesterov_direction = pseudo_gradient[index] + momentum * updated_velocity
        velocity.append(updated_velocity)
        post_outer.append(value - learning_rate * nesterov_direction)
    return post_outer, {"step": step, "velocity": velocity}


def _nested_float_close(left: Any, right: Any, *, tolerance: float) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return False
        return all(
            _nested_float_close(left[key], right[key], tolerance=tolerance)
            for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(
            _nested_float_close(a, b, tolerance=tolerance)
            for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float) or isinstance(right, float):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def _max_abs_delta(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return float("inf")
    return max((abs(a - b) for a, b in zip(left, right, strict=True)), default=0.0)


def _with_stable_artifact_size(
    report: DilocoOptimizerSmokeReport,
) -> DilocoOptimizerSmokeReport:
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
    if first.startswith("DiLoCo optimizer smoke requires --synthetic"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("DiLoCo optimizer smoke currently requires"):
        return "argument_validation", "invalid_arguments", first
    if first.startswith("diloco_optimizer_reference_failed:"):
        return (
            "optimizer_reference_check",
            "optimizer_reference_check_failed",
            first,
        )
    return "diloco_optimizer_smoke", "diloco_optimizer_smoke_failed", first
