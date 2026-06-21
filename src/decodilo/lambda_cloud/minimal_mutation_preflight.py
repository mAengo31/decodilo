"""Preflight for M027 fake-server-only minimal mutation execution."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.minimal_mutation_audit import LambdaMinimalMutationAuditReport
from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)
from decodilo.lambda_cloud.minimal_mutation_execution_policy import (
    LambdaMinimalMutationPolicyReport,
    evaluate_minimal_mutation_execution_policy,
)
from decodilo.lambda_cloud.minimal_mutation_safety_checks import (
    LambdaMinimalMutationSafetyCheckReport,
    run_minimal_mutation_safety_checks,
)


class LambdaMinimalMutationPreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preflight_passed: bool
    m027_authorization_status: str = "present"
    execution_context: LambdaMinimalMutationExecutionContext
    execution_policy: LambdaMinimalMutationPolicyReport
    safety_checks: LambdaMinimalMutationSafetyCheckReport
    minimal_mutation_audit: LambdaMinimalMutationAuditReport | None = None
    fake_server_ready: bool
    real_execution_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_minimal_mutation_preflight(
    *,
    context: LambdaMinimalMutationExecutionContext,
    m027_authorization_present: bool = True,
    operation_spec_present: bool = True,
    budget_lock_present: bool = True,
    idempotency_plan_present: bool = True,
    resource_scope_present: bool = True,
    teardown_plan_present: bool = True,
    termination_policy_present: bool = True,
    audit_report: LambdaMinimalMutationAuditReport | None = None,
) -> LambdaMinimalMutationPreflightReport:
    policy = evaluate_minimal_mutation_execution_policy(
        context=context,
        m027_authorization_present=m027_authorization_present,
        operation_spec_present=operation_spec_present,
        budget_lock_present=budget_lock_present,
        idempotency_plan_present=idempotency_plan_present,
        resource_scope_present=resource_scope_present,
        teardown_plan_present=teardown_plan_present,
        termination_policy_present=termination_policy_present,
    )
    safety = run_minimal_mutation_safety_checks(context)
    blockers = [*policy.blockers, *safety.blockers]
    if audit_report is not None and not audit_report.audit_passed:
        blockers.extend(audit_report.blockers)
    return LambdaMinimalMutationPreflightReport(
        preflight_passed=not blockers,
        execution_context=context,
        execution_policy=policy,
        safety_checks=safety,
        minimal_mutation_audit=audit_report,
        fake_server_ready=context.fake_execution_candidate,
        blockers=blockers,
        warnings=[
            "M027 preflight permits fake-server execution only; real launch remains disabled."
        ],
    )


def write_lambda_minimal_mutation_preflight_report(
    path: str | Path,
    report: LambdaMinimalMutationPreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_minimal_mutation_preflight_report(
    path: str | Path,
) -> LambdaMinimalMutationPreflightReport:
    return LambdaMinimalMutationPreflightReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
