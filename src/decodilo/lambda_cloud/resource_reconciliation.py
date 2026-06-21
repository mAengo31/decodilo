"""Read-only Lambda resource reconciliation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.live_resource_ledger import (
    LambdaLiveResourceLedgerReport,
    load_lambda_live_ledger_report,
)
from decodilo.lambda_cloud.shape_matcher import load_discovery_any
from decodilo.lambda_cloud.teardown_plan import LambdaTeardownPlan, load_lambda_teardown_plan

LambdaResourceConflict = Literal[
    "missing_region",
    "missing_image",
    "missing_ssh_key",
    "missing_filesystem",
    "unmanaged_billable_resource",
]


class LambdaUnmanagedResourceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    unmanaged_count: int = 0
    unmanaged_billable_count: int = 0
    unmanaged_instance_ids: list[str] = Field(default_factory=list)
    manual_review_required: bool = False


class LambdaResourceReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    planned_nodes: int
    discovered_instances: int
    running_instances: int
    unmanaged_instances: int
    unmanaged_billable_instances: int
    planned_resource_conflicts: list[LambdaResourceConflict] = Field(default_factory=list)
    ssh_key_matches: bool | None = None
    filesystem_matches: bool | None = None
    region_matches: bool
    image_matches: bool | None = None
    unmanaged_summary: LambdaUnmanagedResourceSummary
    resource_reconciliation_passed: bool
    manual_review_required: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    no_mutations_performed: bool = True
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_lambda_resources(
    *,
    discovery_report: str | Path,
    ledger_report: str | Path | LambdaLiveResourceLedgerReport,
    launch_plan: str | Path | LambdaLaunchPlan,
    teardown_plan: str | Path | LambdaTeardownPlan,
) -> LambdaResourceReconciliationReport:
    discovery = load_discovery_any(discovery_report)
    ledger = (
        ledger_report
        if isinstance(ledger_report, LambdaLiveResourceLedgerReport)
        else load_lambda_live_ledger_report(ledger_report)
    )
    plan = (
        launch_plan
        if isinstance(launch_plan, LambdaLaunchPlan)
        else load_lambda_launch_plan(launch_plan)
    )
    teardown = (
        teardown_plan
        if isinstance(teardown_plan, LambdaTeardownPlan)
        else load_lambda_teardown_plan(teardown_plan)
    )
    warnings: list[str] = []
    errors: list[str] = []
    conflicts: list[LambdaResourceConflict] = []
    regions = {region.region_id for region in getattr(discovery, "regions", [])}
    images = {image.image_id for image in getattr(discovery, "images", [])}
    image_names = {image.name for image in getattr(discovery, "images", [])}
    ssh_keys = {key.key_id for key in getattr(discovery, "ssh_keys", [])} | {
        key.name for key in getattr(discovery, "ssh_keys", [])
    }
    filesystems = {fs.filesystem_id for fs in getattr(discovery, "filesystems", [])} | {
        fs.name for fs in getattr(discovery, "filesystems", [])
    }
    region_matches = not regions or plan.region in regions
    if not region_matches:
        conflicts.append("missing_region")
        errors.append(f"planned region missing from discovery: {plan.region}")
    image_matches = None
    if plan.image:
        image_matches = plan.image in images or plan.image in image_names
        if not image_matches:
            conflicts.append("missing_image")
            errors.append(f"planned image missing from discovery: {plan.image}")
    ssh_key_matches = None
    if plan.ssh_key_ref:
        ssh_key_matches = plan.ssh_key_ref in ssh_keys
        if not ssh_key_matches:
            conflicts.append("missing_ssh_key")
            errors.append(f"planned SSH key missing from discovery: {plan.ssh_key_ref}")
    filesystem_matches = None
    if plan.filesystem_refs:
        missing = [ref for ref in plan.filesystem_refs if ref not in filesystems]
        filesystem_matches = not missing
        if missing:
            conflicts.append("missing_filesystem")
            errors.append("planned filesystem refs missing from discovery: " + ",".join(missing))
    if teardown.teardown_enabled or teardown.live_resource_ids:
        errors.append("teardown plan must remain disabled and contain no live resource IDs")
    if ledger.billable_state_count and ledger.unmanaged_count:
        conflicts.append("unmanaged_billable_resource")
        warnings.append("unmanaged billable Lambda resources require manual review")
    instances = list(getattr(discovery, "instances", getattr(discovery, "running_instances", [])))
    running = sum(
        1
        for instance in instances
        if str(instance.status).lower() in {"active", "running", "pending", "booting"}
    )
    unmanaged_summary = LambdaUnmanagedResourceSummary(
        unmanaged_count=ledger.unmanaged_count,
        unmanaged_billable_count=ledger.billable_state_count if ledger.unmanaged_count else 0,
        unmanaged_instance_ids=ledger.unmanaged_instance_ids,
        manual_review_required=ledger.manual_review_required,
    )
    return LambdaResourceReconciliationReport(
        planned_nodes=plan.node_count,
        discovered_instances=len(instances),
        running_instances=running,
        unmanaged_instances=ledger.unmanaged_count,
        unmanaged_billable_instances=unmanaged_summary.unmanaged_billable_count,
        planned_resource_conflicts=conflicts,
        ssh_key_matches=ssh_key_matches,
        filesystem_matches=filesystem_matches,
        region_matches=region_matches,
        image_matches=image_matches,
        unmanaged_summary=unmanaged_summary,
        resource_reconciliation_passed=not errors,
        manual_review_required=ledger.manual_review_required,
        warnings=warnings,
        errors=errors,
    )


def load_lambda_resource_reconciliation_report(
    path: str | Path,
) -> LambdaResourceReconciliationReport:
    return LambdaResourceReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_resource_reconciliation_report(
    path: str | Path,
    report: LambdaResourceReconciliationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
