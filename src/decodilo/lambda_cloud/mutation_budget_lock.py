"""Review-only budget lock artifact for future Lambda mutation requests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m020_report import (
    LambdaM020ReadinessReport,
    load_lambda_m020_report,
)


class LambdaMutationBudgetLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    max_budget: float = Field(ge=0)
    max_runtime_minutes: int = Field(gt=0)
    max_instances: int = Field(gt=0)
    selected_price_record_id: str
    price_snapshot_id: str
    safety_buffer_adjusted_cost: float = Field(ge=0)
    approval_manifest_hash: str
    created_at_utc: str | None = None
    expires_at_utc: str | None = None
    lock_hash: str
    locked: bool = True
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_limits(self) -> LambdaMutationBudgetLock:
        if self.max_budget > 50:
            raise ValueError("budget lock exceeds first-launch $50 limit")
        if self.max_runtime_minutes > 30:
            raise ValueError("budget lock exceeds first-launch 30 minute limit")
        if self.max_instances > 1:
            raise ValueError("budget lock exceeds first-launch one instance limit")
        if not self.locked:
            raise ValueError("budget lock must be locked")
        if self.expires_at_utc is not None:
            expires = _parse_utc(self.expires_at_utc)
            if expires <= datetime.now(timezone.utc):
                raise ValueError("budget lock is expired")
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("budget lock cannot enable Lambda mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMutationBudgetLockReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    budget_lock: LambdaMutationBudgetLock
    lock_valid: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_mutation_budget_lock(
    *,
    m020_report: str | Path | LambdaM020ReadinessReport,
    approval_manifest_hash: str = "review-only-approval-hash",
) -> LambdaMutationBudgetLock:
    report = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    policy = report.first_launch_policy_report.policy
    selected_price = report.price_reconciliation.selected_price_record_id or "unknown-price"
    snapshot_id = report.price_reconciliation.price_snapshot_id
    material = "|".join(
        [
            report.launch_plan_ref,
            str(policy.max_run_budget),
            str(policy.max_runtime_minutes),
            str(policy.max_instances),
            selected_price,
            snapshot_id,
            approval_manifest_hash,
        ]
    )
    return LambdaMutationBudgetLock(
        run_id=Path(report.launch_plan_ref).stem or "lambda-run",
        max_budget=policy.max_run_budget,
        max_runtime_minutes=policy.max_runtime_minutes,
        max_instances=policy.max_instances,
        selected_price_record_id=selected_price,
        price_snapshot_id=snapshot_id,
        safety_buffer_adjusted_cost=(
            report.price_reconciliation.safety_buffer_adjusted_cost
        ),
        approval_manifest_hash=approval_manifest_hash,
        lock_hash=hashlib.sha256(material.encode("utf-8")).hexdigest(),
    )


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_lambda_mutation_budget_lock(path: str | Path) -> LambdaMutationBudgetLock:
    return LambdaMutationBudgetLock.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_mutation_budget_lock(path: str | Path, lock: LambdaMutationBudgetLock) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lock.to_json(), encoding="utf-8")
