"""Offline Lambda billing estimate helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_models import LambdaUsageEstimate


class LambdaBillingEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    estimated_hourly_cost: float = Field(ge=0)
    estimated_total_cost: float = Field(ge=0)
    planned_hours: float = Field(ge=0)
    usage_estimate: LambdaUsageEstimate | None = None
    live_billing_used: bool = False
    warnings: list[str] = Field(default_factory=list)


def estimate_lambda_billing(
    *,
    hourly_price: float,
    node_count: int,
    planned_hours: float,
    usage_estimate: LambdaUsageEstimate | None = None,
) -> LambdaBillingEstimate:
    hourly = max(0.0, hourly_price) * max(0, node_count)
    return LambdaBillingEstimate(
        estimated_hourly_cost=hourly,
        estimated_total_cost=hourly * max(0.0, planned_hours),
        planned_hours=planned_hours,
        usage_estimate=usage_estimate,
        warnings=["billing estimate is fixture/manual only; no live billing API was used"],
    )
