"""Local/offline tiny real training mechanics smoke command."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TinyRealTrainingSmokeStatus = Literal["passed", "failed"]

SYNTHETIC_X = [0.0, 1.0, 2.0]
SYNTHETIC_Y = [1.0, 3.0, 5.0]
INITIAL_PARAMETERS = {"weight": 0.5, "bias": -0.25}
ADAMW_HYPERPARAMETERS = {
    "learning_rate": 0.05,
    "beta1": 0.9,
    "beta2": 0.999,
    "epsilon": 1e-8,
    "weight_decay": 0.01,
}
TOLERANCE = 1e-8


class TinyRealTrainingSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    tiny_real_training_smoke_status: TinyRealTrainingSmokeStatus
    command: str = "dev tiny-real-training-smoke"
    synthetic: bool
    model: str
    steps_requested: int
    steps_completed: int
    optimizer: str
    cpu_only: bool = True
    network_used: bool = False
    package_install_attempted: bool = False
    download_attempted: bool = False
    dataset_download_attempted: bool = False
    model_download_attempted: bool = False
    training_attempted: bool
    real_training_mechanics_exercised: bool
    real_model_training_claimed: bool = False
    paper_scale_training_claimed: bool = False
    torch_required: bool = False
    gpu_required: bool = False
    background_process_started: bool = False
    initial_loss: float | None = None
    final_loss: float | None = None
    loss_finite_check_passed: bool = False
    parameter_update_check_passed: bool = False
    gradient_check_passed: bool = False
    optimizer_state_check_passed: bool = False
    deterministic_replay_check_passed: bool | None = None
    deterministic_replay_check_reason: str | None = None
    max_abs_error: float | None = None
    synthetic_x: list[float] = Field(default_factory=list)
    synthetic_y: list[float] = Field(default_factory=list)
    initial_parameters: dict[str, float] = Field(default_factory=dict)
    gradients: dict[str, float] = Field(default_factory=dict)
    finite_difference_gradients: dict[str, float] = Field(default_factory=dict)
    updated_parameters: dict[str, float] = Field(default_factory=dict)
    replay_updated_parameters: dict[str, float] = Field(default_factory=dict)
    optimizer_state: dict[str, Any] = Field(default_factory=dict)
    hyperparameters: dict[str, float] = Field(default_factory=dict)
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
    def _validate_report(self) -> TinyRealTrainingSmokeReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("tiny real training smoke report cannot enable launch")
        if (
            self.network_used
            or self.package_install_attempted
            or self.download_attempted
            or self.dataset_download_attempted
            or self.model_download_attempted
            or not self.cpu_only
            or self.torch_required
            or self.gpu_required
            or self.background_process_started
        ):
            raise ValueError("tiny real training smoke report carries unsafe behavior")
        if self.real_model_training_claimed or self.paper_scale_training_claimed:
            raise ValueError("tiny real training smoke cannot overclaim training scale")
        if (
            self.tiny_real_training_smoke_status == "passed"
            and (
                self.synthetic is not True
                or self.model != "tiny-linear"
                or self.steps_requested != 1
                or self.steps_completed != 1
                or self.optimizer != "adamw"
                or not self.training_attempted
                or not self.real_training_mechanics_exercised
                or not self.loss_finite_check_passed
                or not self.parameter_update_check_passed
                or not self.gradient_check_passed
                or not self.optimizer_state_check_passed
                or not self.deterministic_replay_check_passed
            )
        ):
            raise ValueError(
                "passing tiny real training smoke requires one verified training step"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_tiny_real_training_smoke(
    *,
    synthetic: bool,
    model: str,
    steps: int,
    optimizer: str,
    out: str | Path,
) -> TinyRealTrainingSmokeReport:
    start = time.monotonic()
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    if not synthetic:
        errors.append("Tiny real training smoke requires --synthetic")
    if model != "tiny-linear":
        errors.append("Tiny real training smoke currently requires --model tiny-linear")
    if steps != 1:
        errors.append("Tiny real training smoke currently requires --steps 1")
    if optimizer != "adamw":
        errors.append("Tiny real training smoke currently requires --optimizer adamw")

    if not errors:
        try:
            metrics = _run_reference_tiny_training_step()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"tiny_real_training_step_failed:{type(exc).__name__}")

    checks = _checks_from_metrics(metrics)
    passed = not errors and all(checks.values())
    failed_check, error_classification, safe_error_message = _classify_failure(errors)
    report = TinyRealTrainingSmokeReport(
        tiny_real_training_smoke_status="passed" if passed else "failed",
        synthetic=synthetic,
        model=model,
        steps_requested=steps,
        steps_completed=1 if passed else 0,
        optimizer=optimizer,
        training_attempted=bool(metrics),
        real_training_mechanics_exercised=passed,
        initial_loss=metrics.get("initial_loss"),
        final_loss=metrics.get("final_loss"),
        **checks,
        deterministic_replay_check_reason=(
            None if checks["deterministic_replay_check_passed"] else "replay_mismatch"
        ),
        max_abs_error=metrics.get("max_abs_error"),
        synthetic_x=list(metrics.get("synthetic_x", SYNTHETIC_X)),
        synthetic_y=list(metrics.get("synthetic_y", SYNTHETIC_Y)),
        initial_parameters=dict(metrics.get("initial_parameters", INITIAL_PARAMETERS)),
        gradients=dict(metrics.get("gradients", {})),
        finite_difference_gradients=dict(
            metrics.get("finite_difference_gradients", {})
        ),
        updated_parameters=dict(metrics.get("updated_parameters", {})),
        replay_updated_parameters=dict(metrics.get("replay_updated_parameters", {})),
        optimizer_state=dict(metrics.get("optimizer_state", {})),
        hyperparameters=dict(ADAMW_HYPERPARAMETERS),
        skipped_checks={
            "dataset_pipeline": "not exercised; synthetic in-memory data only",
            "model_download": "not exercised; tiny linear model is created locally",
            "distributed_diloco": "not exercised by this single-process smoke",
            "paper_scale_training": "not claimed by this bounded local smoke",
            "torch": "not required; pure-Python arithmetic is used",
            "gpu": "not required; CPU-only arithmetic is used",
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
    loaded = load_tiny_real_training_smoke_report(target)
    final_report = _with_stable_artifact_size(loaded)
    target.write_text(final_report.to_json(), encoding="utf-8")
    return final_report


def load_tiny_real_training_smoke_report(
    path: str | Path,
) -> TinyRealTrainingSmokeReport:
    return TinyRealTrainingSmokeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _run_reference_tiny_training_step() -> dict[str, Any]:
    first = _compute_training_step()
    replay = _compute_training_step()
    replay_error = _max_dict_abs_error(
        first["updated_parameters"],
        replay["updated_parameters"],
    )
    max_abs_error = max(first["gradient_max_abs_error"], replay_error)
    return {
        **first,
        "replay_updated_parameters": replay["updated_parameters"],
        "deterministic_replay_check_passed": replay_error <= TOLERANCE,
        "max_abs_error": max_abs_error,
    }


def _compute_training_step() -> dict[str, Any]:
    params = dict(INITIAL_PARAMETERS)
    initial_loss = _mse_loss(params)
    gradients = _mse_gradients(params)
    finite_difference_gradients = _finite_difference_gradients(params)
    gradient_error = _max_dict_abs_error(gradients, finite_difference_gradients)
    updated_params, optimizer_state = _adamw_update(
        params=params,
        gradients=gradients,
    )
    final_loss = _mse_loss(updated_params)
    return {
        "synthetic_x": list(SYNTHETIC_X),
        "synthetic_y": list(SYNTHETIC_Y),
        "initial_parameters": params,
        "initial_loss": initial_loss,
        "gradients": gradients,
        "finite_difference_gradients": finite_difference_gradients,
        "gradient_max_abs_error": gradient_error,
        "updated_parameters": updated_params,
        "optimizer_state": optimizer_state,
        "final_loss": final_loss,
    }


def _mse_loss(params: dict[str, float]) -> float:
    losses = []
    for x_value, y_value in zip(SYNTHETIC_X, SYNTHETIC_Y, strict=True):
        prediction = params["weight"] * x_value + params["bias"]
        residual = prediction - y_value
        losses.append(residual * residual)
    return sum(losses) / len(losses)


def _mse_gradients(params: dict[str, float]) -> dict[str, float]:
    scale = 2.0 / len(SYNTHETIC_X)
    grad_weight = 0.0
    grad_bias = 0.0
    for x_value, y_value in zip(SYNTHETIC_X, SYNTHETIC_Y, strict=True):
        prediction = params["weight"] * x_value + params["bias"]
        residual = prediction - y_value
        grad_weight += residual * x_value
        grad_bias += residual
    return {
        "weight": scale * grad_weight,
        "bias": scale * grad_bias,
    }


def _finite_difference_gradients(params: dict[str, float]) -> dict[str, float]:
    epsilon = 1e-6
    gradients: dict[str, float] = {}
    for name in ("weight", "bias"):
        plus = dict(params)
        minus = dict(params)
        plus[name] += epsilon
        minus[name] -= epsilon
        gradients[name] = (_mse_loss(plus) - _mse_loss(minus)) / (2.0 * epsilon)
    return gradients


def _adamw_update(
    *,
    params: dict[str, float],
    gradients: dict[str, float],
) -> tuple[dict[str, float], dict[str, Any]]:
    lr = ADAMW_HYPERPARAMETERS["learning_rate"]
    beta1 = ADAMW_HYPERPARAMETERS["beta1"]
    beta2 = ADAMW_HYPERPARAMETERS["beta2"]
    epsilon = ADAMW_HYPERPARAMETERS["epsilon"]
    weight_decay = ADAMW_HYPERPARAMETERS["weight_decay"]
    updated: dict[str, float] = {}
    exp_avg: dict[str, float] = {}
    exp_avg_sq: dict[str, float] = {}
    for name, value in params.items():
        gradient = gradients[name]
        exp_avg[name] = (1.0 - beta1) * gradient
        exp_avg_sq[name] = (1.0 - beta2) * gradient * gradient
        bias_corrected_avg = exp_avg[name] / (1.0 - beta1)
        bias_corrected_avg_sq = exp_avg_sq[name] / (1.0 - beta2)
        adam_step = bias_corrected_avg / (math.sqrt(bias_corrected_avg_sq) + epsilon)
        decayed = value * (1.0 - lr * weight_decay)
        updated[name] = decayed - lr * adam_step
    return updated, {"step": 1, "exp_avg": exp_avg, "exp_avg_sq": exp_avg_sq}


def _checks_from_metrics(metrics: dict[str, Any]) -> dict[str, bool]:
    initial_loss = metrics.get("initial_loss")
    final_loss = metrics.get("final_loss")
    updated = metrics.get("updated_parameters", {})
    initial = metrics.get("initial_parameters", {})
    optimizer_state = metrics.get("optimizer_state", {})
    return {
        "loss_finite_check_passed": (
            isinstance(initial_loss, float)
            and isinstance(final_loss, float)
            and math.isfinite(initial_loss)
            and math.isfinite(final_loss)
        ),
        "parameter_update_check_passed": (
            bool(updated)
            and any(
                abs(float(updated[name]) - float(initial[name])) > TOLERANCE
                for name in initial
            )
        ),
        "gradient_check_passed": (
            metrics.get("gradient_max_abs_error") is not None
            and float(metrics["gradient_max_abs_error"]) <= TOLERANCE
        ),
        "optimizer_state_check_passed": (
            optimizer_state.get("step") == 1
            and set(optimizer_state.get("exp_avg", {})) == {"weight", "bias"}
            and set(optimizer_state.get("exp_avg_sq", {})) == {"weight", "bias"}
        ),
        "deterministic_replay_check_passed": bool(
            metrics.get("deterministic_replay_check_passed", False)
        ),
    }


def _max_dict_abs_error(
    left: dict[str, float],
    right: dict[str, float],
) -> float:
    return max(abs(float(left[name]) - float(right[name])) for name in left)


def _classify_failure(errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not errors:
        return None, None, None
    first = errors[0]
    if "requires" in first:
        return "argument_validation", "invalid_arguments", first
    return "tiny_real_training_step", "training_mechanics_check_failed", first


def _with_stable_artifact_size(
    report: TinyRealTrainingSmokeReport,
) -> TinyRealTrainingSmokeReport:
    current = report
    for _ in range(8):
        encoded = current.to_json().encode("utf-8")
        size = len(encoded)
        if current.artifact_bytes == size:
            return current
        current = current.model_copy(update={"artifact_bytes": size})
    return current
