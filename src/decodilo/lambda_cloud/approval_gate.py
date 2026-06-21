"""Human approval gate for future Lambda lifecycle work."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_manifest import (
    LambdaApprovalStatus,
    LambdaHumanApprovalManifest,
    load_lambda_approval_manifest,
)
from decodilo.lambda_cloud.first_launch_policy import LambdaFirstLaunchPolicy
from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan


class LambdaApprovalGateReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_status: LambdaApprovalStatus = "not_requested"
    approval_passed: bool = False
    missing_acknowledgements: list[str] = Field(default_factory=list)
    mismatched_limits: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_approval_gate(
    *,
    approval_manifest: LambdaHumanApprovalManifest | None,
    launch_plan: LambdaLaunchPlan,
    policy: LambdaFirstLaunchPolicy | None = None,
) -> LambdaApprovalGateReport:
    if approval_manifest is None:
        return LambdaApprovalGateReport(
            approval_status="not_requested",
            warnings=["human approval manifest missing"],
            errors=["missing_human_approval"],
        )
    effective = policy or LambdaFirstLaunchPolicy()
    missing_ack = approval_manifest.operator_acknowledgements.missing()
    mismatches: list[str] = []
    if approval_manifest.approved_max_instances > effective.max_instances:
        mismatches.append("approved_max_instances exceeds policy")
    if approval_manifest.approved_max_runtime_minutes > effective.max_runtime_minutes:
        mismatches.append("approved_max_runtime_minutes exceeds policy")
    if approval_manifest.approved_max_budget > effective.max_run_budget:
        mismatches.append("approved_max_budget exceeds policy")
    if approval_manifest.approved_instance_type != launch_plan.instance_type:
        mismatches.append("approved_instance_type differs from launch plan")
    if approval_manifest.approved_region != launch_plan.region:
        mismatches.append("approved_region differs from launch plan")
    if approval_manifest.approval_status == "approved_for_future_real_launch_review":
        mismatches.append("real launch review approval is forbidden in M020")
    errors = [*missing_ack, *mismatches]
    passed = (
        not errors
        and approval_manifest.approval_status == "approved_for_future_fake_launch_lifecycle"
    )
    warnings = ["approval is review metadata only; launch remains disabled"]
    if approval_manifest.approval_status == "incomplete":
        warnings.append("approval manifest is incomplete")
    return LambdaApprovalGateReport(
        approval_status=approval_manifest.approval_status,
        approval_passed=passed,
        missing_acknowledgements=missing_ack,
        mismatched_limits=mismatches,
        warnings=warnings,
        errors=errors,
    )


def evaluate_lambda_approval_gate_from_path(
    *,
    approval_manifest_path: str | Path | None,
    launch_plan: LambdaLaunchPlan,
    policy: LambdaFirstLaunchPolicy | None = None,
) -> LambdaApprovalGateReport:
    manifest = (
        None
        if approval_manifest_path is None
        else load_lambda_approval_manifest(approval_manifest_path)
    )
    return evaluate_lambda_approval_gate(
        approval_manifest=manifest,
        launch_plan=launch_plan,
        policy=policy,
    )


def load_lambda_approval_gate_report(path: str | Path) -> LambdaApprovalGateReport:
    return LambdaApprovalGateReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_approval_gate_report(path: str | Path, report: LambdaApprovalGateReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
