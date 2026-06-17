"""Report metric invariant validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetricValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)


def validate_metrics(
    metrics: dict[str, Any],
    *,
    final_global_version: int | None = None,
) -> MetricValidationResult:
    errors: list[str] = []
    total = int(metrics.get("total_tokens_processed", 0))
    useful = int(metrics.get("useful_tokens_accepted", 0))
    wasted = int(metrics.get("wasted_tokens", 0))
    goodput = float(metrics.get("goodput_ratio", 0.0))
    if useful > total:
        errors.append("useful_tokens_accepted exceeds total_tokens_processed")
    if wasted != total - useful:
        errors.append(
            "wasted_tokens does not equal total_tokens_processed - useful_tokens_accepted"
        )
    if not 0.0 <= goodput <= 1.0:
        errors.append("goodput_ratio is outside [0, 1]")
    total_cost = metrics.get("cost_per_total_token")
    useful_cost = metrics.get("cost_per_useful_token")
    if total_cost is not None and useful_cost is not None and useful <= total:
        if float(useful_cost) < float(total_cost):
            errors.append("cost_per_useful_token is below cost_per_total_token")
    update_messages = int(metrics.get("global_update_messages_sent", 0))
    update_acks = int(metrics.get("global_update_acks", 0))
    if update_acks > update_messages:
        errors.append("global_update_acks exceeds global_update_messages_sent")
    if int(metrics.get("duplicate_global_update_acks", 0)) < 0:
        errors.append("duplicate_global_update_acks is negative")
    if final_global_version is not None:
        committed = int(metrics.get("committed_sync_rounds", 0))
        if committed > final_global_version:
            errors.append("committed_sync_rounds exceeds final_global_version")
    return MetricValidationResult(passed=not errors, errors=errors)


def validate_report_payload(report: dict[str, Any]) -> MetricValidationResult:
    result = validate_metrics(
        dict(report.get("metrics", {})),
        final_global_version=int(report.get("final_global_version", 0)),
    )
    errors = list(result.errors)
    if bool(report.get("trainer_nonfinite_detected", False)):
        errors.append("trainer_nonfinite_detected is true")
    state_bytes = report.get("trainer_state_bytes_estimate")
    if state_bytes is not None and int(state_bytes) <= 0:
        errors.append("trainer_state_bytes_estimate must be positive when reported")
    return MetricValidationResult(passed=not errors, errors=errors)
