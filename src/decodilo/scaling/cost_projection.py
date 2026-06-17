"""Cost projection helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CostProjection:
    raw_cost: float
    safety_adjusted_cost: float
    expected_cost_per_total_token: float
    expected_cost_per_useful_token: float
    break_even_goodput_vs_single_cluster: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def project_cost(
    *,
    price_per_instance_hour: float,
    num_instances: int,
    planned_hours: float,
    expected_goodput_ratio: float,
    expected_useful_tokens: int,
    safety_buffer_pct: float = 0.15,
) -> CostProjection:
    if price_per_instance_hour < 0 or num_instances <= 0 or planned_hours <= 0:
        raise ValueError("price, instances, and hours must be valid")
    if not 0 < expected_goodput_ratio <= 1:
        raise ValueError("expected_goodput_ratio must be in (0, 1]")
    if expected_useful_tokens <= 0:
        raise ValueError("expected_useful_tokens must be positive")
    raw = price_per_instance_hour * num_instances * planned_hours
    adjusted = raw * (1 + safety_buffer_pct)
    total_tokens = expected_useful_tokens / expected_goodput_ratio
    return CostProjection(
        raw_cost=raw,
        safety_adjusted_cost=adjusted,
        expected_cost_per_total_token=raw / total_tokens,
        expected_cost_per_useful_token=raw / expected_useful_tokens,
        break_even_goodput_vs_single_cluster=1 / num_instances,
    )

