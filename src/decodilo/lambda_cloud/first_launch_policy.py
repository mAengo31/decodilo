"""Policy-only first Lambda launch limits."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan
from decodilo.lambda_cloud.live_resource_ledger import LambdaLiveResourceLedgerReport
from decodilo.lambda_cloud.price_reconciliation import LambdaPriceReconciliationReport
from decodilo.lambda_cloud.resource_reconciliation import LambdaResourceReconciliationReport
from decodilo.lambda_cloud.teardown_plan import LambdaTeardownPlan


class LambdaFirstLaunchPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_instances: int = Field(default=1, gt=0)
    max_runtime_minutes: int = Field(default=30, gt=0)
    max_run_budget: float = Field(default=50.0, ge=0)
    require_teardown_plan: bool = True
    require_termination_verification_plan: bool = True
    require_resource_ledger: bool = True
    require_budget_manifest: bool = True
    require_price_reconciliation: bool = True
    require_live_read_only_discovery: bool = True
    require_read_only_audit: bool = True
    require_human_approval: bool = True
    require_no_unmanaged_billable_resources: bool = True
    require_cloud_launch_disabled_in_current_build: bool = True


class LambdaFirstLaunchPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy: LambdaFirstLaunchPolicy
    policy_passed: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_first_launch_policy(
    *,
    launch_plan: LambdaLaunchPlan,
    teardown_plan: LambdaTeardownPlan | None = None,
    ledger_report: LambdaLiveResourceLedgerReport | None = None,
    price_reconciliation: LambdaPriceReconciliationReport | None = None,
    resource_reconciliation: LambdaResourceReconciliationReport | None = None,
    budget_manifest_present: bool = False,
    approval_present: bool = False,
    live_discovery_present: bool = False,
    read_only_audit_present: bool = False,
    policy: LambdaFirstLaunchPolicy | None = None,
) -> LambdaFirstLaunchPolicyReport:
    effective = policy or LambdaFirstLaunchPolicy()
    violations: list[str] = []
    warnings = ["policy is advisory; Lambda launch remains disabled"]
    if launch_plan.node_count > effective.max_instances:
        violations.append("too_many_instances")
    if launch_plan.max_runtime_minutes > effective.max_runtime_minutes:
        violations.append("runtime_too_long")
    if launch_plan.max_run_budget > effective.max_run_budget:
        violations.append("budget_limit_too_high")
    if effective.require_teardown_plan and teardown_plan is None:
        violations.append("missing_teardown_plan")
    if teardown_plan is not None and not teardown_plan.verification_steps:
        violations.append("missing_termination_verification_plan")
    if effective.require_resource_ledger and ledger_report is None:
        violations.append("missing_resource_ledger")
    if effective.require_budget_manifest and not budget_manifest_present:
        violations.append("missing_budget_manifest")
    if effective.require_price_reconciliation and (
        price_reconciliation is None or not price_reconciliation.price_reconciliation_passed
    ):
        violations.append("missing_or_failed_price_reconciliation")
    if (
        resource_reconciliation is not None
        and not resource_reconciliation.resource_reconciliation_passed
    ):
        violations.append("failed_resource_reconciliation")
    if effective.require_live_read_only_discovery and not live_discovery_present:
        violations.append("missing_live_read_only_discovery")
    if effective.require_read_only_audit and not read_only_audit_present:
        violations.append("missing_read_only_audit")
    if effective.require_human_approval and not approval_present:
        violations.append("missing_human_approval")
    if (
        effective.require_no_unmanaged_billable_resources
        and ledger_report is not None
        and ledger_report.billable_state_count
        and ledger_report.unmanaged_count
    ):
        violations.append("unmanaged_billable_resources")
    if effective.require_cloud_launch_disabled_in_current_build and (
        launch_plan.launch_allowed or launch_plan.launch_enabled
    ):
        violations.append("cloud_launch_not_disabled")
    return LambdaFirstLaunchPolicyReport(
        policy=effective,
        policy_passed=not violations,
        violations=violations,
        warnings=warnings,
    )


def load_lambda_first_launch_policy_report(path: str | Path) -> LambdaFirstLaunchPolicyReport:
    return LambdaFirstLaunchPolicyReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_first_launch_policy_report(
    path: str | Path,
    report: LambdaFirstLaunchPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
