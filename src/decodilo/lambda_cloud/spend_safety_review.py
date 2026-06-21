"""Spend safety review for M025 final Lambda pre-launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport, load_lambda_m020_report
from decodilo.lambda_cloud.mutation_budget_lock import (
    LambdaMutationBudgetLock,
    load_lambda_mutation_budget_lock,
)


class LambdaSpendSafetyReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_schema_version: int = 1
    review_id: str = "lambda-spend-safety-review-m025"
    m020_report_ref: str
    budget_lock_ref: str | None = None
    max_budget: float
    planned_hours: float
    max_runtime_minutes: int
    planned_instances: int
    estimated_cost: float
    safety_buffer_adjusted_cost: float
    projected_remaining_credits: float | None = None
    spend_safety_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSpendSafetyReport = LambdaSpendSafetyReview


def review_lambda_spend_safety(
    *,
    m020_report: str | Path | LambdaM020ReadinessReport,
    budget_lock: str | Path | LambdaMutationBudgetLock | None = None,
    allow_sample_or_stale_prices: bool = False,
) -> LambdaSpendSafetyReview:
    report, report_ref = _load_m020(m020_report)
    lock, lock_ref = _load_lock(budget_lock)
    price = report.price_reconciliation
    policy = report.first_launch_policy_report
    blockers: list[str] = []
    warnings: list[str] = []
    max_budget = lock.max_budget if lock is not None else price.max_run_budget
    max_runtime = lock.max_runtime_minutes if lock is not None else 30
    max_instances = lock.max_instances if lock is not None else price.planned_instances
    if max_budget > 50:
        blockers.append("max budget exceeds 50 USD")
    if price.planned_hours > 0.5 or max_runtime > 30:
        blockers.append("runtime exceeds 30 minute first-launch policy")
    if max_instances != 1:
        blockers.append("planned instances must equal 1")
    if not price.price_reconciliation_passed:
        blockers.append("price reconciliation did not pass")
    if lock is None:
        blockers.append("budget lock missing")
    elif not lock.locked:
        blockers.append("budget lock is not locked")
    if price.is_sample_data and not allow_sample_or_stale_prices:
        blockers.append("sample price data cannot support future launch review")
    if not policy.policy_passed:
        warnings.append("first launch policy report did not pass cleanly")
    if price.projected_remaining_credits is not None and price.projected_remaining_credits < 0:
        blockers.append("projected remaining credits are negative")
    return LambdaSpendSafetyReview(
        m020_report_ref=report_ref,
        budget_lock_ref=lock_ref,
        max_budget=max_budget,
        planned_hours=price.planned_hours,
        max_runtime_minutes=max_runtime,
        planned_instances=max_instances,
        estimated_cost=price.base_estimated_cost,
        safety_buffer_adjusted_cost=price.safety_buffer_adjusted_cost,
        projected_remaining_credits=price.projected_remaining_credits,
        spend_safety_passed=not blockers,
        blockers=blockers,
        warnings=[
            *warnings,
            "Future real launch still requires fresh price review.",
        ],
    )


def _load_m020(
    value: str | Path | LambdaM020ReadinessReport,
) -> tuple[LambdaM020ReadinessReport, str]:
    if isinstance(value, LambdaM020ReadinessReport):
        return value, "<in-memory>"
    return load_lambda_m020_report(value), str(value)


def _load_lock(
    value: str | Path | LambdaMutationBudgetLock | None,
) -> tuple[LambdaMutationBudgetLock | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, LambdaMutationBudgetLock):
        return value, "<in-memory>"
    return load_lambda_mutation_budget_lock(value), str(value)


def load_lambda_spend_safety_review(path: str | Path) -> LambdaSpendSafetyReview:
    return LambdaSpendSafetyReview.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_spend_safety_review(
    path: str | Path,
    review: LambdaSpendSafetyReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(review.to_json(), encoding="utf-8")
