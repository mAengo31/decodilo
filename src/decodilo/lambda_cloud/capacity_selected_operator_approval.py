"""Operator approval for the capacity-history-selected Lambda candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    CAPACITY_SELECTED_CANDIDATE,
)

LambdaCapacitySelectedOperatorApprovalStatus = Literal[
    "not_provided",
    "approved_for_future_m046_capacity_selected_launch_review",
    "declined_wait_for_live_availability",
    "declined_manual_candidate_selection",
]

_ACK_FIELDS = (
    "understands_selected_candidate_a100",
    "understands_larger_than_lifecycle_smoke",
    "understands_catalog_backed_unless_live_evidence",
    "understands_h100_pcie_excluded_for_capacity",
    "understands_m046_may_return_capacity_error",
    "understands_no_automatic_launch_retry",
    "understands_one_instance_only",
    "understands_max_budget_50",
    "understands_max_runtime_30_minutes",
    "understands_existing_ssh_key_attached_no_ssh",
    "understands_no_setup_cloud_init_or_training",
    "understands_no_restart_create_delete",
    "understands_owned_termination_required_if_created",
    "understands_termination_verified_with_read_only_lambda",
    "understands_os_shutdown_insufficient",
    "understands_future_review_only_not_immediate_launch",
)


class LambdaCapacitySelectedOperatorApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str = CAPACITY_SELECTED_CANDIDATE
    approval_status: LambdaCapacitySelectedOperatorApprovalStatus = "not_provided"
    operator_name: str | None = None
    understands_selected_candidate_a100: bool = False
    understands_larger_than_lifecycle_smoke: bool = False
    understands_catalog_backed_unless_live_evidence: bool = False
    understands_h100_pcie_excluded_for_capacity: bool = False
    understands_m046_may_return_capacity_error: bool = False
    understands_no_automatic_launch_retry: bool = False
    understands_one_instance_only: bool = False
    understands_max_budget_50: bool = False
    understands_max_runtime_30_minutes: bool = False
    understands_existing_ssh_key_attached_no_ssh: bool = False
    understands_no_setup_cloud_init_or_training: bool = False
    understands_no_restart_create_delete: bool = False
    understands_owned_termination_required_if_created: bool = False
    understands_termination_verified_with_read_only_lambda: bool = False
    understands_os_shutdown_insufficient: bool = False
    understands_future_review_only_not_immediate_launch: bool = False
    approval_complete: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaCapacitySelectedOperatorApproval:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-selected approval cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCapacitySelectedOperatorApprovalReport = LambdaCapacitySelectedOperatorApproval


def build_lambda_capacity_selected_operator_approval(
    *,
    approve_future_m046: bool = False,
    decline_wait: bool = False,
    decline_manual_selection: bool = False,
    acknowledge_all: bool = False,
    operator_name: str | None = None,
) -> LambdaCapacitySelectedOperatorApproval:
    requested = [approve_future_m046, decline_wait, decline_manual_selection]
    blockers: list[str] = []
    if sum(1 for item in requested if item) > 1:
        blockers.append("exactly_one_capacity_selected_operator_choice_required")
    ack_values = {field: acknowledge_all for field in _ACK_FIELDS}
    status: LambdaCapacitySelectedOperatorApprovalStatus = "not_provided"
    complete = False
    if approve_future_m046 and not blockers:
        missing = [field for field, value in ack_values.items() if not value]
        if missing:
            blockers.extend(f"missing_acknowledgement:{field}" for field in missing)
        else:
            status = "approved_for_future_m046_capacity_selected_launch_review"
            complete = True
    elif decline_wait and not blockers:
        status = "declined_wait_for_live_availability"
        complete = True
    elif decline_manual_selection and not blockers:
        status = "declined_manual_candidate_selection"
        complete = True
    elif not blockers:
        blockers.append("capacity_selected_operator_decision_not_provided")
    return LambdaCapacitySelectedOperatorApproval(
        approval_status=status,
        operator_name=operator_name,
        approval_complete=complete,
        blockers=sorted(set(blockers)),
        warnings=[
            "operator approval is future-review only",
            "M045 does not authorize immediate launch",
        ],
        **ack_values,
    )


def load_lambda_capacity_selected_operator_approval(
    path: str | Path,
) -> LambdaCapacitySelectedOperatorApproval:
    return LambdaCapacitySelectedOperatorApproval.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_operator_approval(
    path: str | Path,
    report: LambdaCapacitySelectedOperatorApproval,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
