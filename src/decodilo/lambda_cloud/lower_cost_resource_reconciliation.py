"""Lower-cost Lambda resource reconciliation for future review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    LambdaStrandLowerCostLaunchPlanReport,
    load_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)

LambdaLowerCostLiveAvailabilityStatus = Literal[
    "available",
    "unavailable",
    "endpoint_inconclusive",
    "unknown",
]


class LambdaLowerCostResourceReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    region_checked: str
    selected_shape: Literal["gpu_1x_h100_pcie"] = "gpu_1x_h100_pcie"
    shape_live_availability_status: LambdaLowerCostLiveAvailabilityStatus
    product_catalog_evidence_status: Literal["present", "not_checked"] = "present"
    ssh_key_selection_status: Literal["passed", "failed"]
    unmanaged_billable_count: int
    resource_reconciliation_passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostResourceReconciliationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost resource reconciliation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_lambda_lower_cost_resources(
    *,
    discovery: LambdaLiveDiscoveryReport,
    launch_plan: LambdaStrandLowerCostLaunchPlanReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
) -> LambdaLowerCostResourceReconciliationReport:
    errors: list[str] = []
    warnings = [
        "live availability may remain unknown until launch",
        "M037R resource reconciliation is read-only and cannot mutate resources",
    ]
    plan = launch_plan.plan
    region = plan.region if plan is not None else "us-west-1"
    if not launch_plan.plan_passed or plan is None:
        errors.extend(launch_plan.blockers or ["lower_cost_launch_plan_failed"])
    if not ssh_key_selection.selection_passed:
        errors.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    unmanaged_count = len(discovery.unmanaged_instances)
    if unmanaged_count > 0:
        errors.append("unmanaged_billable_resources_present")
    availability = _availability(discovery)
    return LambdaLowerCostResourceReconciliationReport(
        region_checked=region,
        shape_live_availability_status=availability,
        ssh_key_selection_status="passed" if ssh_key_selection.selection_passed else "failed",
        unmanaged_billable_count=unmanaged_count,
        resource_reconciliation_passed=not errors,
        warnings=warnings,
        errors=errors,
    )


def reconcile_lambda_lower_cost_resources_from_paths(
    *,
    discovery_report: str | Path,
    launch_plan: str | Path,
    ssh_key_selection: str | Path,
) -> LambdaLowerCostResourceReconciliationReport:
    return reconcile_lambda_lower_cost_resources(
        discovery=load_lambda_live_discovery_report(discovery_report),
        launch_plan=load_lambda_strand_lower_cost_launch_plan_report(launch_plan),
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
    )


def _availability(
    discovery: LambdaLiveDiscoveryReport,
    shape: str = "gpu_1x_h100_pcie",
) -> LambdaLowerCostLiveAvailabilityStatus:
    if not discovery.instance_types:
        return "endpoint_inconclusive"
    names = {item.name for item in discovery.instance_types} | {
        item.instance_type_id for item in discovery.instance_types
    }
    return "available" if shape in names else "unknown"


def load_lambda_lower_cost_resource_reconciliation(
    path: str | Path,
) -> LambdaLowerCostResourceReconciliationReport:
    return LambdaLowerCostResourceReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_resource_reconciliation(
    path: str | Path,
    report: LambdaLowerCostResourceReconciliationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
