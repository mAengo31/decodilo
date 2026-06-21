"""Lambda launch blocker aggregation for M020 planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.approval_gate import LambdaApprovalGateReport
from decodilo.lambda_cloud.first_launch_policy import LambdaFirstLaunchPolicyReport
from decodilo.lambda_cloud.price_reconciliation import LambdaPriceReconciliationReport
from decodilo.lambda_cloud.resource_reconciliation import LambdaResourceReconciliationReport

LambdaLaunchBlockerCategory = Literal[
    "missing_live_discovery",
    "missing_audit",
    "missing_price_reconciliation",
    "missing_resource_reconciliation",
    "missing_teardown_plan",
    "missing_budget_manifest",
    "missing_human_approval",
    "unmanaged_billable_resources",
    "sample_or_stale_pricing",
    "shape_not_discovered",
    "price_missing",
    "budget_exceeded",
    "runtime_too_long",
    "too_many_instances",
    "remote_backend_not_ready",
    "launch_code_disabled",
    "mutation_guard_enabled",
    "launch_not_supported_in_current_milestone",
]


class LambdaLaunchBlocker(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: LambdaLaunchBlockerCategory
    severity: Literal["warning", "blocker"] = "blocker"
    message: str


class LambdaLaunchBlockerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    blockers: list[LambdaLaunchBlocker]
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_blocker_report(
    *,
    live_discovery_present: bool,
    audit_present: bool,
    teardown_present: bool,
    budget_manifest_present: bool,
    price_reconciliation: LambdaPriceReconciliationReport | None,
    resource_reconciliation: LambdaResourceReconciliationReport | None,
    first_launch_policy: LambdaFirstLaunchPolicyReport | None,
    approval_gate: LambdaApprovalGateReport | None,
    remote_backend_ready: bool = False,
) -> LambdaLaunchBlockerReport:
    blockers: list[LambdaLaunchBlocker] = []
    if not live_discovery_present:
        blockers.append(_blocker("missing_live_discovery", "live read-only discovery is missing"))
    if not audit_present:
        blockers.append(_blocker("missing_audit", "read-only audit is missing"))
    if price_reconciliation is None:
        blockers.append(_blocker("missing_price_reconciliation", "price reconciliation is missing"))
    elif not price_reconciliation.price_reconciliation_passed:
        for risk in price_reconciliation.price_risks:
            category: LambdaLaunchBlockerCategory = {
                "sample_price": "sample_or_stale_pricing",
                "stale_price": "sample_or_stale_pricing",
                "missing_price": "price_missing",
                "ambiguous_price": "price_missing",
                "budget_exceeded": "budget_exceeded",
            }.get(risk, "price_missing")
            blockers.append(_blocker(category, f"price reconciliation risk: {risk}"))
        if price_reconciliation.shape_match.match_status != "matched":
            blockers.append(_blocker("shape_not_discovered", "planned shape was not matched"))
    if resource_reconciliation is None:
        blockers.append(
            _blocker("missing_resource_reconciliation", "resource reconciliation is missing")
        )
    else:
        if not resource_reconciliation.resource_reconciliation_passed:
            blockers.append(
                _blocker("missing_resource_reconciliation", "resource reconciliation failed")
            )
        if resource_reconciliation.unmanaged_billable_instances:
            blockers.append(
                _blocker(
                    "unmanaged_billable_resources",
                    "unmanaged billable resources exist",
                )
            )
    if not teardown_present:
        blockers.append(_blocker("missing_teardown_plan", "teardown plan is missing"))
    if not budget_manifest_present:
        blockers.append(_blocker("missing_budget_manifest", "budget manifest is missing"))
    if first_launch_policy is not None:
        for violation in first_launch_policy.violations:
            if violation == "too_many_instances":
                blockers.append(
                    _blocker("too_many_instances", "planned instance count exceeds policy")
                )
            elif violation == "runtime_too_long":
                blockers.append(_blocker("runtime_too_long", "planned runtime exceeds policy"))
    if approval_gate is None or not approval_gate.approval_passed:
        blockers.append(_blocker("missing_human_approval", "human approval gate has not passed"))
    if not remote_backend_ready:
        blockers.append(
            _blocker("remote_backend_not_ready", "remote artifact backend is not ready")
        )
    blockers.append(_blocker("launch_code_disabled", "Lambda launch code is disabled"))
    blockers.append(
        LambdaLaunchBlocker(
            category="mutation_guard_enabled",
            severity="warning",
            message="mutation guard remains enabled and denies mutating operations",
        )
    )
    blockers.append(
        _blocker(
            "launch_not_supported_in_current_milestone",
            "M020 is planning-only and cannot launch Lambda resources",
        )
    )
    return LambdaLaunchBlockerReport(blockers=blockers)


def _blocker(category: LambdaLaunchBlockerCategory, message: str) -> LambdaLaunchBlocker:
    return LambdaLaunchBlocker(category=category, message=message)


def load_lambda_launch_blocker_report(path: str | Path) -> LambdaLaunchBlockerReport:
    return LambdaLaunchBlockerReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_launch_blocker_report(path: str | Path, report: LambdaLaunchBlockerReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
