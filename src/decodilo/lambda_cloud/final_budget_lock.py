"""M028 final budget lock for M029 authorization review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport, load_lambda_m020_report


class LambdaFinalBudgetLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    lock_id: str = "lambda-final-budget-lock-m028"
    m020_report_ref: str
    max_budget: float = Field(ge=0)
    max_runtime_minutes: int = Field(gt=0)
    max_instances: int = Field(gt=0)
    planned_hours: float = Field(gt=0)
    selected_price_record_id: str | None
    price_snapshot_id: str
    safety_buffer_adjusted_cost: float = Field(ge=0)
    projected_remaining_credits: float | None = None
    safety_buffer_included: bool = True
    lock_hash: str
    locked_for_m029_authorization_only: bool = True
    budget_lock_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalBudgetLock:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 final budget lock cannot enable launch or mutation")
        if not self.locked_for_m029_authorization_only:
            raise ValueError("M028 final budget lock must be review-only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaFinalBudgetLockReport = LambdaFinalBudgetLock


def build_lambda_final_budget_lock(
    m020_report: str | Path | LambdaM020ReadinessReport,
) -> LambdaFinalBudgetLock:
    report = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    price = report.price_reconciliation
    policy = report.first_launch_policy_report.policy
    blockers: list[str] = []
    if price.max_run_budget > 50 or policy.max_run_budget > 50:
        blockers.append("max budget exceeds 50 USD")
    if price.planned_hours > 0.5 or policy.max_runtime_minutes > 30:
        blockers.append("runtime exceeds 30 minutes")
    if price.planned_instances != 1 or policy.max_instances != 1:
        blockers.append("planned instances must equal one")
    if price.selected_price_record_id is None:
        blockers.append("selected price record missing")
    if price.projected_remaining_credits < 0:
        blockers.append("projected remaining credits negative")
    if not price.price_reconciliation_passed:
        blockers.append("price reconciliation did not pass")
    material = "|".join(
        [
            str(price.selected_price_record_id),
            price.price_snapshot_id,
            str(price.safety_buffer_adjusted_cost),
            str(price.max_run_budget),
            str(policy.max_runtime_minutes),
        ]
    )
    report_ref = (
        "<in-memory>"
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else str(m020_report)
    )
    return LambdaFinalBudgetLock(
        m020_report_ref=report_ref,
        max_budget=min(price.max_run_budget, policy.max_run_budget),
        max_runtime_minutes=policy.max_runtime_minutes,
        max_instances=policy.max_instances,
        planned_hours=price.planned_hours,
        selected_price_record_id=price.selected_price_record_id,
        price_snapshot_id=price.price_snapshot_id,
        safety_buffer_adjusted_cost=price.safety_buffer_adjusted_cost,
        projected_remaining_credits=price.projected_remaining_credits,
        lock_hash=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        budget_lock_passed=not blockers,
        blockers=blockers,
        warnings=["Final budget lock authorizes M029 review only; M028 cannot launch."],
    )


def load_lambda_final_budget_lock(path: str | Path) -> LambdaFinalBudgetLock:
    return LambdaFinalBudgetLock.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_final_budget_lock(path: str | Path, lock: LambdaFinalBudgetLock) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lock.to_json(), encoding="utf-8")
