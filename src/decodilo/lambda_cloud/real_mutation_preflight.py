"""Preflight for the disabled Lambda real mutation skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.mutation_budget_lock import (
    LambdaMutationBudgetLock,
    load_lambda_mutation_budget_lock,
)
from decodilo.lambda_cloud.mutation_idempotency_plan import (
    LambdaMutationIdempotencyPlan,
    load_lambda_mutation_idempotency_plan,
)
from decodilo.lambda_cloud.mutation_resource_scope import (
    LambdaMutationResourceScope,
    load_lambda_mutation_resource_scope,
)
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuardReport,
)
from decodilo.lambda_cloud.real_mutation_skeleton_audit import (
    LambdaRealMutationSkeletonAuditReport,
    load_lambda_real_mutation_skeleton_audit_report,
)


class LambdaRealMutationPreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preflight_status: str
    skeleton_audit_summary: dict[str, object] | None = None
    execution_guard_summary: dict[str, object] | None = None
    budget_lock_summary: dict[str, object] | None = None
    idempotency_summary: dict[str, object] | None = None
    resource_scope_summary: dict[str, object] | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_lambda_real_mutation_preflight(
    *,
    skeleton_audit: str | Path | LambdaRealMutationSkeletonAuditReport | None = None,
    execution_guard: LambdaRealMutationExecutionGuardReport | None = None,
    budget_lock: str | Path | LambdaMutationBudgetLock | None = None,
    idempotency_plan: str | Path | LambdaMutationIdempotencyPlan | None = None,
    resource_scope: str | Path | LambdaMutationResourceScope | None = None,
) -> LambdaRealMutationPreflightReport:
    blockers: list[str] = ["current milestone forbids real mutation execution"]
    warnings = ["mutation skeleton present but disabled; no execution path available"]
    audit = _load_audit(skeleton_audit)
    lock = _load_budget_lock_optional(budget_lock)
    idempotency = _load_idempotency_optional(idempotency_plan)
    scope = _load_scope_optional(resource_scope)
    if audit is None:
        warnings.append("skeleton audit missing")
    elif not audit.passed:
        blockers.append("skeleton audit failed")
    if execution_guard is None:
        warnings.append("execution guard report missing")
    elif execution_guard.execution_guard_passed_for_execution:
        blockers.append("execution guard unexpectedly passed for execution")
    if lock is None:
        warnings.append("budget lock missing")
    if idempotency is None:
        warnings.append("idempotency plan missing")
    if scope is None:
        warnings.append("resource scope missing")
    return LambdaRealMutationPreflightReport(
        preflight_status="blocked_for_execution",
        skeleton_audit_summary=None
        if audit is None
        else {
            "passed": audit.passed,
            "real_mutation_code_detected": audit.real_mutation_code_detected,
            "launch_allowed": audit.launch_allowed,
        },
        execution_guard_summary=None
        if execution_guard is None
        else {
            "review_only_passed": execution_guard.review_only_passed,
            "execution_guard_passed_for_execution": (
                execution_guard.execution_guard_passed_for_execution
            ),
            "blockers": execution_guard.blockers,
        },
        budget_lock_summary=None
        if lock is None
        else {
            "locked": lock.locked,
            "max_budget": lock.max_budget,
            "max_runtime_minutes": lock.max_runtime_minutes,
            "max_instances": lock.max_instances,
            "launch_allowed": lock.launch_allowed,
        },
        idempotency_summary=None
        if idempotency is None
        else {
            "operation": idempotency.idempotency_key.operation,
            "key": idempotency.idempotency_key.key,
            "launch_allowed": idempotency.launch_allowed,
        },
        resource_scope_summary=None
        if scope is None
        else {
            "scope_id": scope.owned_scope.scope_id,
            "terminate_unowned_allowed": scope.terminate_unowned_allowed,
            "launch_allowed": scope.launch_allowed,
        },
        blockers=blockers,
        warnings=warnings,
    )


def _load_audit(
    value: str | Path | LambdaRealMutationSkeletonAuditReport | None,
) -> LambdaRealMutationSkeletonAuditReport | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealMutationSkeletonAuditReport):
        return value
    return load_lambda_real_mutation_skeleton_audit_report(value)


def _load_budget_lock_optional(
    value: str | Path | LambdaMutationBudgetLock | None,
) -> LambdaMutationBudgetLock | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationBudgetLock):
        return value
    return load_lambda_mutation_budget_lock(value)


def _load_idempotency_optional(
    value: str | Path | LambdaMutationIdempotencyPlan | None,
) -> LambdaMutationIdempotencyPlan | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationIdempotencyPlan):
        return value
    return load_lambda_mutation_idempotency_plan(value)


def _load_scope_optional(
    value: str | Path | LambdaMutationResourceScope | None,
) -> LambdaMutationResourceScope | None:
    if value is None:
        return None
    if isinstance(value, LambdaMutationResourceScope):
        return value
    return load_lambda_mutation_resource_scope(value)


def write_lambda_real_mutation_preflight_report(
    path: str | Path,
    report: LambdaRealMutationPreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
