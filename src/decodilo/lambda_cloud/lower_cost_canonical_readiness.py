"""Canonical lower-cost readiness report for future M039 review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_price_reconciliation import (
    LambdaLowerCostPriceReconciliationReport,
    load_lambda_lower_cost_price_reconciliation,
)
from decodilo.lambda_cloud.lower_cost_resource_reconciliation import (
    LambdaLowerCostResourceReconciliationReport,
    load_lambda_lower_cost_resource_reconciliation,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    LambdaStrandLowerCostLaunchPlanReport,
    load_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)


class LambdaLowerCostCanonicalReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    readiness_schema_version: int = 1
    shape: Literal["gpu_1x_h100_pcie"] = "gpu_1x_h100_pcie"
    gpu_type: Literal["H100 PCIe"] = "H100 PCIe"
    gpus_per_instance: Literal[1] = 1
    region: str
    quantity: int
    selected_ssh_key_hash: str | None = None
    strand_payload_compatible: bool
    price_reconciliation_passed: bool
    resource_reconciliation_passed: bool
    unmanaged_billable_count: int
    live_availability_status: str
    planned_30min_cost: float | None = None
    buffered_30min_cost: float | None = None
    readiness_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostCanonicalReadinessReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost canonical readiness cannot enable launch")
        if self.readiness_passed and self.blockers:
            raise ValueError("lower-cost canonical readiness cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_canonical_readiness(
    *,
    launch_plan: LambdaStrandLowerCostLaunchPlanReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    price_reconciliation: LambdaLowerCostPriceReconciliationReport,
    resource_reconciliation: LambdaLowerCostResourceReconciliationReport,
) -> LambdaLowerCostCanonicalReadinessReport:
    blockers: list[str] = []
    warnings = [
        "lower-cost canonical readiness is future-review only",
        "live availability may remain unknown until launch",
    ]
    plan = launch_plan.plan
    if not launch_plan.plan_passed or plan is None:
        blockers.extend(launch_plan.blockers or ["lower_cost_launch_plan_failed"])
    if not ssh_key_selection.selection_passed:
        blockers.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    if not ssh_key_selection.selected_ssh_key_name_redacted_or_hash:
        blockers.append("selected_existing_ssh_key_hash_missing")
    if not price_reconciliation.price_reconciliation_passed:
        blockers.extend(
            price_reconciliation.errors or ["lower_cost_price_reconciliation_failed"]
        )
    if not resource_reconciliation.resource_reconciliation_passed:
        blockers.extend(
            resource_reconciliation.errors or ["lower_cost_resource_reconciliation_failed"]
        )
    strand_payload_compatible = bool(plan is not None and launch_plan.plan_passed)
    quantity = 0 if plan is None else plan.quantity
    if quantity != 1:
        blockers.append("quantity_must_equal_one")
    if plan is not None and (
        plan.setup_scripts_allowed
        or plan.cloud_init_allowed
        or plan.training_allowed
        or plan.ssh_allowed
    ):
        blockers.append("setup_cloud_init_ssh_or_training_enabled")
    if resource_reconciliation.unmanaged_billable_count > 0:
        blockers.append("unmanaged_billable_resources_present")
    if resource_reconciliation.shape_live_availability_status == "endpoint_inconclusive":
        warnings.append("instance-type endpoint inconclusive; product catalog evidence used")
    return LambdaLowerCostCanonicalReadinessReport(
        region="us-west-1" if plan is None else plan.region,
        quantity=quantity,
        selected_ssh_key_hash=ssh_key_selection.selected_ssh_key_name_redacted_or_hash,
        strand_payload_compatible=strand_payload_compatible,
        price_reconciliation_passed=price_reconciliation.price_reconciliation_passed,
        resource_reconciliation_passed=resource_reconciliation.resource_reconciliation_passed,
        unmanaged_billable_count=resource_reconciliation.unmanaged_billable_count,
        live_availability_status=resource_reconciliation.shape_live_availability_status,
        planned_30min_cost=price_reconciliation.base_estimated_cost,
        buffered_30min_cost=price_reconciliation.safety_buffer_adjusted_cost,
        readiness_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def build_lambda_lower_cost_canonical_readiness_from_paths(
    *,
    launch_plan: str | Path,
    ssh_key_selection: str | Path,
    price_reconciliation: str | Path,
    resource_reconciliation: str | Path,
) -> LambdaLowerCostCanonicalReadinessReport:
    return build_lambda_lower_cost_canonical_readiness(
        launch_plan=load_lambda_strand_lower_cost_launch_plan_report(launch_plan),
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
        price_reconciliation=load_lambda_lower_cost_price_reconciliation(
            price_reconciliation
        ),
        resource_reconciliation=load_lambda_lower_cost_resource_reconciliation(
            resource_reconciliation
        ),
    )


def load_lambda_lower_cost_canonical_readiness(
    path: str | Path,
) -> LambdaLowerCostCanonicalReadinessReport:
    return LambdaLowerCostCanonicalReadinessReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_canonical_readiness(
    path: str | Path,
    report: LambdaLowerCostCanonicalReadinessReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
