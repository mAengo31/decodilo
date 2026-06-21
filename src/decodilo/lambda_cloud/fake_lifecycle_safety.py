"""Safety checks for fake Lambda lifecycle execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_manifest import LambdaHumanApprovalManifest
from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan
from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport


class FakeLambdaLifecycleSafetyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False


def validate_fake_lifecycle_safety(
    *,
    m020_report: LambdaM020ReadinessReport,
    approval_manifest: LambdaHumanApprovalManifest,
    launch_plan: LambdaLaunchPlan,
    fake_mode: bool,
) -> FakeLambdaLifecycleSafetyReport:
    errors: list[str] = []
    warnings = ["fake lifecycle safety gate is local-only"]
    if not fake_mode:
        errors.append("fake_mode must be true")
    if launch_plan.launch_allowed or launch_plan.launch_enabled:
        errors.append("launch plan must remain non-launchable")
    if m020_report.billable_action_performed or m020_report.mutating_operations:
        errors.append("M020 report contains billable or mutating activity")
    if not m020_report.price_reconciliation.price_reconciliation_passed:
        errors.append("price reconciliation must pass")
    if not m020_report.resource_reconciliation.resource_reconciliation_passed:
        errors.append("resource reconciliation must pass")
    if not m020_report.first_launch_policy_report.policy_passed:
        errors.append("first launch policy must pass")
    if m020_report.resource_reconciliation.unmanaged_billable_instances:
        errors.append("unmanaged billable resources block fake lifecycle")
    if approval_manifest.approval_status != "approved_for_future_fake_launch_lifecycle":
        errors.append("approval must be approved_for_future_fake_launch_lifecycle")
    if approval_manifest.operator_acknowledgements.missing():
        errors.append("approval acknowledgements are incomplete")
    return FakeLambdaLifecycleSafetyReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
    )

