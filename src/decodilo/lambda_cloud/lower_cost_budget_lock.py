"""Budget lock for the lower-cost future M039 review path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    LambdaLowerCostCanonicalReadinessReport,
    load_lambda_lower_cost_canonical_readiness,
)


class LambdaLowerCostBudgetLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_shape: str = "gpu_1x_h100_pcie"
    planned_runtime_minutes: int = 30
    max_budget: float = 50.0
    estimated_cost: float | None = None
    buffered_estimated_cost: float | None = None
    non_sample_price: bool
    budget_lock_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostBudgetLock:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost budget lock cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_budget_lock(
    canonical_readiness: LambdaLowerCostCanonicalReadinessReport,
    *,
    planned_runtime_minutes: int = 30,
    max_budget: float = 50.0,
) -> LambdaLowerCostBudgetLock:
    blockers: list[str] = []
    if not canonical_readiness.readiness_passed:
        blockers.extend(canonical_readiness.blockers or ["canonical_readiness_failed"])
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")
    if canonical_readiness.quantity != 1:
        blockers.append("quantity_must_equal_one")
    if canonical_readiness.buffered_30min_cost is None:
        blockers.append("buffered_cost_missing")
    elif canonical_readiness.buffered_30min_cost >= max_budget:
        blockers.append("buffered_cost_exceeds_budget")
    non_sample = canonical_readiness.price_reconciliation_passed
    if not non_sample:
        blockers.append("non_sample_price_required")
    return LambdaLowerCostBudgetLock(
        planned_runtime_minutes=planned_runtime_minutes,
        max_budget=max_budget,
        estimated_cost=canonical_readiness.planned_30min_cost,
        buffered_estimated_cost=canonical_readiness.buffered_30min_cost,
        non_sample_price=non_sample,
        budget_lock_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=["lower-cost budget lock is future-review only"],
    )


def build_lambda_lower_cost_budget_lock_from_path(
    *,
    canonical_readiness: str | Path,
    planned_runtime_minutes: int = 30,
    max_budget: float = 50.0,
) -> LambdaLowerCostBudgetLock:
    return build_lambda_lower_cost_budget_lock(
        load_lambda_lower_cost_canonical_readiness(canonical_readiness),
        planned_runtime_minutes=planned_runtime_minutes,
        max_budget=max_budget,
    )


def load_lambda_lower_cost_budget_lock(path: str | Path) -> LambdaLowerCostBudgetLock:
    return LambdaLowerCostBudgetLock.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_budget_lock(
    path: str | Path,
    report: LambdaLowerCostBudgetLock,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
