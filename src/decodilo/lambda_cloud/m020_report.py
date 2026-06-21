"""Combined M020 Lambda read-only readiness report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_gate import (
    LambdaApprovalGateReport,
    evaluate_lambda_approval_gate,
)
from decodilo.lambda_cloud.approval_manifest import (
    LambdaHumanApprovalManifest,
    load_lambda_approval_manifest,
)
from decodilo.lambda_cloud.first_launch_policy import (
    LambdaFirstLaunchPolicyReport,
    evaluate_first_launch_policy,
)
from decodilo.lambda_cloud.launch_blockers import (
    LambdaLaunchBlockerReport,
    build_lambda_launch_blocker_report,
)
from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaLaunchShapeResolutionReport,
    load_lambda_launch_shape_resolution_report,
)
from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.live_resource_ledger import (
    load_lambda_live_ledger_report,
)
from decodilo.lambda_cloud.price_reconciliation import (
    LambdaPriceReconciliationReport,
    reconcile_lambda_price,
)
from decodilo.lambda_cloud.read_only_audit import (
    load_lambda_read_only_audit_report,
)
from decodilo.lambda_cloud.readiness_summary import (
    LambdaReadinessSummary,
    build_lambda_readiness_summary,
)
from decodilo.lambda_cloud.resource_reconciliation import (
    LambdaResourceReconciliationReport,
    reconcile_lambda_resources,
)
from decodilo.lambda_cloud.teardown_plan import load_lambda_teardown_plan
from decodilo.pricing.snapshots import load_price_snapshot


class LambdaM020ReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    discovery_report_ref: str
    audit_report_ref: str
    ledger_report_ref: str
    launch_plan_ref: str
    teardown_plan_ref: str
    price_snapshot_ref: str
    approval_manifest_ref: str | None = None
    price_reconciliation: LambdaPriceReconciliationReport
    resource_reconciliation: LambdaResourceReconciliationReport
    first_launch_policy_report: LambdaFirstLaunchPolicyReport
    approval_gate_report: LambdaApprovalGateReport
    launch_blocker_report: LambdaLaunchBlockerReport
    readiness_summary: LambdaReadinessSummary
    secret_scan_status: str = "not_checked"
    live_api_used: bool
    read_operations: int
    mutating_operations: int
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m020_report(
    *,
    discovery_report: str | Path,
    read_only_audit: str | Path,
    ledger: str | Path,
    launch_plan: str | Path,
    teardown_plan: str | Path,
    price_snapshot: str | Path,
    credits: float,
    max_run_budget: float,
    planned_hours: float,
    safety_buffer_percentage: float,
    approval_manifest: str | Path | None = None,
    gpu_type: str | None = None,
    allow_sample_prices: bool = False,
    allow_stale_prices: bool = False,
    shape_resolution: str | Path | LambdaLaunchShapeResolutionReport | None = None,
) -> LambdaM020ReadinessReport:
    discovery = load_lambda_live_discovery_report(discovery_report)
    audit = load_lambda_read_only_audit_report(read_only_audit)
    ledger_report = load_lambda_live_ledger_report(ledger)
    plan = load_lambda_launch_plan(launch_plan)
    teardown = load_lambda_teardown_plan(teardown_plan)
    snapshot = load_price_snapshot(price_snapshot)
    selected_gpu_type = gpu_type or _infer_gpu_type(plan, discovery)
    price_report = reconcile_lambda_price(
        discovery_report_path=discovery_report,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type=selected_gpu_type,
        credits=credits,
        planned_hours=planned_hours,
        max_run_budget=max_run_budget,
        safety_buffer_percentage=safety_buffer_percentage,
        allow_sample_prices=allow_sample_prices,
        allow_stale_prices=allow_stale_prices,
        shape_resolution=_load_optional_shape_resolution(shape_resolution),
    )
    resource_report = reconcile_lambda_resources(
        discovery_report=discovery_report,
        ledger_report=ledger_report,
        launch_plan=plan,
        teardown_plan=teardown,
    )
    approval = _load_optional_approval(approval_manifest)
    approval_report = evaluate_lambda_approval_gate(
        approval_manifest=approval,
        launch_plan=plan,
    )
    first_launch_report = evaluate_first_launch_policy(
        launch_plan=plan,
        teardown_plan=teardown,
        ledger_report=ledger_report,
        price_reconciliation=price_report,
        resource_reconciliation=resource_report,
        budget_manifest_present=bool(plan.budget_manifest_ref),
        approval_present=approval is not None,
        live_discovery_present=True,
        read_only_audit_present=True,
    )
    blocker_report = build_lambda_launch_blocker_report(
        live_discovery_present=True,
        audit_present=True,
        teardown_present=True,
        budget_manifest_present=bool(plan.budget_manifest_ref),
        price_reconciliation=price_report,
        resource_reconciliation=resource_report,
        first_launch_policy=first_launch_report,
        approval_gate=approval_report,
        remote_backend_ready=False,
    )
    readiness = build_lambda_readiness_summary(
        blocker_report=blocker_report,
        approval_passed_for_fake_lifecycle=approval_report.approval_passed,
    )
    warnings = [
        *price_report.warnings,
        *resource_report.warnings,
        *first_launch_report.warnings,
        *approval_report.warnings,
        *readiness.warnings,
    ]
    errors = [
        *price_report.errors,
        *resource_report.errors,
        *first_launch_report.violations,
        *approval_report.errors,
    ]
    return LambdaM020ReadinessReport(
        discovery_report_ref=str(discovery_report),
        audit_report_ref=str(read_only_audit),
        ledger_report_ref=str(ledger),
        launch_plan_ref=str(launch_plan),
        teardown_plan_ref=str(teardown_plan),
        price_snapshot_ref=str(price_snapshot),
        approval_manifest_ref=None if approval_manifest is None else str(approval_manifest),
        price_reconciliation=price_report,
        resource_reconciliation=resource_report,
        first_launch_policy_report=first_launch_report,
        approval_gate_report=approval_report,
        launch_blocker_report=blocker_report,
        readiness_summary=readiness,
        secret_scan_status="not_checked",
        live_api_used=discovery.live_api_used,
        read_operations=audit.read_operations,
        mutating_operations=audit.mutating_operations,
        billable_action_performed=(
            discovery.billable_action_performed
            or audit.billable_action_performed
            or ledger_report.billable_action_performed
        ),
        warnings=warnings,
        errors=errors,
    )


def _infer_gpu_type(plan: LambdaLaunchPlan, discovery) -> str:  # noqa: ANN001
    for shape in discovery.instance_types:
        if shape.instance_type_id == plan.instance_type or shape.name == plan.instance_type:
            if shape.gpu_type:
                return shape.gpu_type
    raise ValueError("gpu_type is required when launch plan shape is not present in discovery")


def _load_optional_approval(path: str | Path | None) -> LambdaHumanApprovalManifest | None:
    return None if path is None else load_lambda_approval_manifest(path)


def _load_optional_shape_resolution(
    value: str | Path | LambdaLaunchShapeResolutionReport | None,
) -> LambdaLaunchShapeResolutionReport | None:
    if value is None or isinstance(value, LambdaLaunchShapeResolutionReport):
        return value
    return load_lambda_launch_shape_resolution_report(value)


def load_lambda_m020_report(path: str | Path) -> LambdaM020ReadinessReport:
    return LambdaM020ReadinessReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m020_report(path: str | Path, report: LambdaM020ReadinessReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
