"""Planning model for temporary or discounted learner pods."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScavengedPodSupply(BaseModel):
    model_config = ConfigDict(frozen=True)

    expected_extra_learners: float = Field(ge=0)
    availability_window_seconds: float = Field(gt=0)
    preemption_rate_per_hour: float = Field(ge=0)
    startup_time_seconds: float = Field(ge=0)
    discount_vs_base: float = Field(ge=0, le=1)
    max_extra_learners: int = Field(ge=0)
    join_leave_frequency: float = Field(ge=0)
    trust_tier: str = "local_trusted"
    data_access_tier: str = "local_only"
    notes: list[str] = Field(default_factory=list)


class ScavengedPodSchedule(BaseModel):
    model_config = ConfigDict(frozen=True)

    supplies: list[ScavengedPodSupply]


class ScavengedComputeEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    expected_extra_useful_tokens: float
    expected_cost_savings: float
    expected_churn_events: float
    expected_artifact_pressure_increase: float
    expected_checkpoint_pressure_increase: float
    warnings: list[str] = Field(default_factory=list)


def estimate_scavenged_compute(
    *,
    supply: ScavengedPodSupply,
    per_learner_token_rate: float,
    base_price_per_learner_hour: float,
    artifact_bytes_per_learner_sync: float,
    checkpoint_bytes_per_learner: float,
) -> ScavengedComputeEstimate:
    if min(per_learner_token_rate, base_price_per_learner_hour) < 0:
        raise ValueError("rates and prices must be nonnegative")
    useful_window = max(0.0, supply.availability_window_seconds - supply.startup_time_seconds)
    preemption_loss = min(1.0, supply.preemption_rate_per_hour * useful_window / 3600)
    effective_learners = min(supply.expected_extra_learners, supply.max_extra_learners)
    useful_tokens = (
        effective_learners
        * useful_window
        * per_learner_token_rate
        * (1 - preemption_loss)
    )
    undiscounted = effective_learners * base_price_per_learner_hour * useful_window / 3600
    cost_savings = undiscounted * supply.discount_vs_base
    churn = effective_learners * supply.join_leave_frequency * useful_window / 3600
    warnings: list[str] = []
    if preemption_loss > 0.5:
        warnings.append("high preemption reduces scavenged value")
    if supply.startup_time_seconds > supply.availability_window_seconds / 2:
        warnings.append("startup time consumes most of the scavenged window")
    if churn > effective_learners:
        warnings.append("churn may exceed update/recovery capacity")
    if supply.trust_tier != "local_trusted" or supply.data_access_tier != "local_only":
        warnings.append("trust/data access tier requires future policy validation")
    return ScavengedComputeEstimate(
        expected_extra_useful_tokens=useful_tokens,
        expected_cost_savings=cost_savings,
        expected_churn_events=churn,
        expected_artifact_pressure_increase=effective_learners * artifact_bytes_per_learner_sync,
        expected_checkpoint_pressure_increase=effective_learners * checkpoint_bytes_per_learner,
        warnings=warnings,
    )
