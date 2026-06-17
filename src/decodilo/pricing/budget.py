"""Budget and burn-rate calculations."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import BudgetExceededError
from decodilo.pricing.models import PriceProfile
from decodilo.pricing.provenance import utc_now_iso


def hourly_cost_for_cluster(num_instances: int, price: PriceProfile) -> float:
    if num_instances <= 0:
        raise ValueError("num_instances must be positive")
    return num_instances * price.price_per_instance_hour


def max_hours_for_budget(credit_amount: float, hourly_cost: float) -> float:
    if credit_amount < 0:
        raise ValueError("credit_amount must be non-negative")
    if hourly_cost <= 0:
        raise ValueError("hourly_cost must be positive")
    return credit_amount / hourly_cost


def estimated_cost_for_run(gpu_hours: float, price_per_gpu_hour: float) -> float:
    if gpu_hours < 0:
        raise ValueError("gpu_hours must be non-negative")
    if price_per_gpu_hour < 0:
        raise ValueError("price_per_gpu_hour must be non-negative")
    return gpu_hours * price_per_gpu_hour


def effective_cost_per_useful_token(actual_cost: float, useful_tokens: int) -> float:
    if actual_cost < 0:
        raise ValueError("actual_cost must be non-negative")
    if useful_tokens <= 0:
        raise ValueError("useful_tokens must be positive")
    return actual_cost / useful_tokens


class BudgetDecision(BaseModel):
    """Result returned by the fail-closed budget guard."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str
    estimated_cost: float = Field(ge=0)
    safety_buffer_amount: float = Field(ge=0)
    safety_buffer_adjusted_cost: float = Field(ge=0)
    projected_remaining_credits: float


class RunBudgetManifest(BaseModel):
    """Durable budget plan for local/cloud-dry-run/cloud modes."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    created_at_utc: str
    provider: str
    mode: str
    price_snapshot_id: str
    selected_price_record_ids: list[str]
    planned_instances: int = Field(gt=0)
    planned_gpus: int = Field(gt=0)
    planned_hours: float = Field(gt=0)
    estimated_gpu_hours: float = Field(ge=0)
    base_estimated_cost: float = Field(ge=0)
    safety_buffer_percentage: float = Field(ge=0)
    safety_buffer_adjusted_cost: float = Field(ge=0)
    max_run_budget: float = Field(ge=0)
    starting_credits: float = Field(ge=0)
    projected_remaining_credits: float
    allow_sample_prices: bool = False
    allow_stale_prices: bool = False
    notes: str = ""


def build_run_budget_manifest(
    *,
    run_id: str,
    provider: str,
    mode: str,
    price_snapshot_id: str,
    selected_price_record_ids: list[str],
    planned_instances: int,
    gpus_per_instance: int,
    planned_hours: float,
    base_estimated_cost: float,
    safety_buffer_percentage: float,
    safety_buffer_adjusted_cost: float,
    max_run_budget: float,
    starting_credits: float,
    projected_remaining_credits: float,
    allow_sample_prices: bool = False,
    allow_stale_prices: bool = False,
    notes: str = "",
) -> RunBudgetManifest:
    return RunBudgetManifest(
        run_id=run_id,
        created_at_utc=utc_now_iso(),
        provider=provider,
        mode=mode,
        price_snapshot_id=price_snapshot_id,
        selected_price_record_ids=selected_price_record_ids,
        planned_instances=planned_instances,
        planned_gpus=planned_instances * gpus_per_instance,
        planned_hours=planned_hours,
        estimated_gpu_hours=planned_instances * gpus_per_instance * planned_hours,
        base_estimated_cost=base_estimated_cost,
        safety_buffer_percentage=safety_buffer_percentage,
        safety_buffer_adjusted_cost=safety_buffer_adjusted_cost,
        max_run_budget=max_run_budget,
        starting_credits=starting_credits,
        projected_remaining_credits=projected_remaining_credits,
        allow_sample_prices=allow_sample_prices,
        allow_stale_prices=allow_stale_prices,
        notes=notes,
    )


@dataclass
class BudgetGuard:
    """Fail-closed guard for planned training spend."""

    starting_credits: float
    estimated_committed_spend: float = 0.0
    actual_observed_spend: float = 0.0
    safety_buffer_pct: float = 0.15

    def __post_init__(self) -> None:
        if self.starting_credits < 0:
            raise ValueError("starting_credits must be non-negative")
        if self.estimated_committed_spend < 0:
            raise ValueError("estimated_committed_spend must be non-negative")
        if self.actual_observed_spend < 0:
            raise ValueError("actual_observed_spend must be non-negative")
        if self.safety_buffer_pct < 0:
            raise ValueError("safety_buffer_pct must be non-negative")

    def check_run(self, *, estimated_run_cost: float, max_run_budget: float) -> BudgetDecision:
        if estimated_run_cost < 0:
            raise ValueError("estimated_run_cost must be non-negative")
        if max_run_budget < 0:
            raise ValueError("max_run_budget must be non-negative")

        buffer_amount = estimated_run_cost * self.safety_buffer_pct
        guarded_cost = estimated_run_cost + buffer_amount
        projected_remaining = (
            self.starting_credits
            - self.estimated_committed_spend
            - self.actual_observed_spend
            - guarded_cost
        )

        if estimated_run_cost > max_run_budget:
            return BudgetDecision(
                allowed=False,
                reason="planned run exceeds max_run_budget",
                estimated_cost=estimated_run_cost,
                safety_buffer_amount=buffer_amount,
                safety_buffer_adjusted_cost=guarded_cost,
                projected_remaining_credits=projected_remaining,
            )
        if projected_remaining < 0:
            return BudgetDecision(
                allowed=False,
                reason="projected remaining credits would be negative",
                estimated_cost=estimated_run_cost,
                safety_buffer_amount=buffer_amount,
                safety_buffer_adjusted_cost=guarded_cost,
                projected_remaining_credits=projected_remaining,
            )
        return BudgetDecision(
            allowed=True,
            reason="within budget",
            estimated_cost=estimated_run_cost,
            safety_buffer_amount=buffer_amount,
            safety_buffer_adjusted_cost=guarded_cost,
            projected_remaining_credits=projected_remaining,
        )

    def require_run_allowed(
        self,
        *,
        estimated_run_cost: float,
        max_run_budget: float,
    ) -> BudgetDecision:
        decision = self.check_run(
            estimated_run_cost=estimated_run_cost,
            max_run_budget=max_run_budget,
        )
        if not decision.allowed:
            raise BudgetExceededError(decision.reason)
        return decision
