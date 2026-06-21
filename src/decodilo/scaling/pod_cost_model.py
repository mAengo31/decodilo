"""Cost estimates for learner-pod scaling candidates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PodCostEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    total_gpus: float
    raw_cost_per_hour: float
    cost_per_total_token: float | None
    cost_per_useful_token: float | None
    cost_per_sample_efficiency_adjusted_token: float | None
    estimated_time_to_target_tokens: float | None = None
    estimated_cost_to_target_tokens: float | None = None
    warnings: list[str] = Field(default_factory=list)


def estimate_pod_cost(
    *,
    learner_count: int,
    total_gpus: float,
    price_per_gpu_hour: float,
    raw_tokens_per_second: float,
    useful_tokens_per_second: float,
    adjusted_tokens_per_second: float,
    target_useful_tokens: float | None = None,
) -> PodCostEstimate:
    if learner_count <= 0 or total_gpus <= 0 or price_per_gpu_hour < 0:
        raise ValueError("learner count, GPUs, and price must be valid")
    hourly = total_gpus * price_per_gpu_hour
    hourly_seconds = 3600.0
    cost_total = _cost_per_token(hourly, hourly_seconds, raw_tokens_per_second)
    cost_useful = _cost_per_token(hourly, hourly_seconds, useful_tokens_per_second)
    cost_adjusted = _cost_per_token(hourly, hourly_seconds, adjusted_tokens_per_second)
    time_to_target = None
    cost_to_target = None
    if target_useful_tokens is not None and adjusted_tokens_per_second > 0:
        time_to_target = target_useful_tokens / adjusted_tokens_per_second
        cost_to_target = hourly * (time_to_target / hourly_seconds)
    warnings = []
    if price_per_gpu_hour == 0:
        warnings.append("price_per_gpu_hour is zero; cost outputs are planning placeholders")
    return PodCostEstimate(
        learner_count=learner_count,
        total_gpus=total_gpus,
        raw_cost_per_hour=hourly,
        cost_per_total_token=cost_total,
        cost_per_useful_token=cost_useful,
        cost_per_sample_efficiency_adjusted_token=cost_adjusted,
        estimated_time_to_target_tokens=time_to_target,
        estimated_cost_to_target_tokens=cost_to_target,
        warnings=warnings,
    )


def _cost_per_token(hourly: float, hourly_seconds: float, tokens_per_second: float) -> float | None:
    if tokens_per_second <= 0:
        return None
    return hourly / (tokens_per_second * hourly_seconds)

