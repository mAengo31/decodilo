"""High-level capacity plan combining cost, size, and bandwidth estimates."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.pricing.snapshots import SnapshotPriceRecord
from decodilo.scaling.bandwidth import BandwidthEstimate, estimate_outer_loop_bandwidth
from decodilo.scaling.cost_projection import CostProjection, project_cost
from decodilo.scaling.model_size import estimate_parameter_bytes, human_readable_bytes


@dataclass(frozen=True)
class CapacityPlan:
    model_bytes: float
    model_size_human: str
    bandwidth: BandwidthEstimate
    cost: CostProjection
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "model_bytes": self.model_bytes,
            "model_size_human": self.model_size_human,
            "bandwidth": self.bandwidth.to_dict(),
            "cost": self.cost.to_dict(),
            "warnings": self.warnings,
        }


def build_capacity_plan(
    *,
    price_record: SnapshotPriceRecord,
    num_instances: int,
    planned_hours: float,
    parameter_count: int,
    bytes_per_parameter: float,
    num_learners: int,
    expected_tokens_per_second: float,
    expected_goodput: float,
    credit_budget: float,
    sync_interval_steps: int = 500,
    local_step_seconds: float = 1.0,
    num_fragments: int = 128,
) -> CapacityPlan:
    if expected_tokens_per_second <= 0:
        raise ValueError("expected_tokens_per_second must be positive")
    useful_tokens = int(expected_tokens_per_second * planned_hours * 3600 * expected_goodput)
    model_bytes = estimate_parameter_bytes(parameter_count, bytes_per_parameter)
    bandwidth = estimate_outer_loop_bandwidth(
        parameter_count=parameter_count,
        bytes_per_parameter=bytes_per_parameter,
        num_learners=num_learners,
        num_fragments=num_fragments,
        sync_interval_steps=sync_interval_steps,
        local_step_seconds=local_step_seconds,
    )
    cost = project_cost(
        price_per_instance_hour=price_record.price_per_instance_hour,
        num_instances=num_instances,
        planned_hours=planned_hours,
        expected_goodput_ratio=expected_goodput,
        expected_useful_tokens=useful_tokens,
    )
    warnings: list[str] = []
    if cost.safety_adjusted_cost > credit_budget:
        warnings.append("budget_exceeded")
    if expected_goodput < 0.5:
        warnings.append("low_goodput")
    if bandwidth.average_bandwidth_gbps > 100:
        warnings.append("high_average_bandwidth")
    return CapacityPlan(
        model_bytes=model_bytes,
        model_size_human=human_readable_bytes(model_bytes),
        bandwidth=bandwidth,
        cost=cost,
        warnings=warnings,
    )
