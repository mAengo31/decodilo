"""Operator approval template for the future lower-cost M039 launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaLowerCostOperatorApprovalStatus = Literal[
    "not_provided",
    "pending_acknowledgement",
    "approved_for_future_m039_lower_cost_launch_attempt",
]

_ACK_FIELDS = [
    "ack_billable_action_possible_future_milestone",
    "ack_one_instance_only",
    "ack_region_us_west_1",
    "ack_max_budget_50",
    "ack_max_runtime_30_min",
    "ack_lower_cost_shape_gpu_1x_h100_pcie",
    "ack_existing_ssh_key_attached_but_no_ssh",
    "ack_no_ssh",
    "ack_no_setup_scripts",
    "ack_no_cloud_init",
    "ack_no_training",
    "ack_no_restart_create_delete",
    "ack_no_ssh_key_create_delete",
    "ack_no_filesystem_create_delete",
    "ack_terminate_owned_instance_required",
    "ack_termination_verification_required",
    "ack_os_shutdown_insufficient",
    "ack_no_automatic_launch_retry",
    "ack_operator_present",
]


class LambdaLowerCostOperatorApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_id: str = "lambda-lower-cost-m039-operator-approval"
    approval_status: LambdaLowerCostOperatorApprovalStatus = "not_provided"
    operator_name: str | None = None
    ack_billable_action_possible_future_milestone: bool = False
    ack_one_instance_only: bool = False
    ack_region_us_west_1: bool = False
    ack_max_budget_50: bool = False
    ack_max_runtime_30_min: bool = False
    ack_lower_cost_shape_gpu_1x_h100_pcie: bool = False
    ack_existing_ssh_key_attached_but_no_ssh: bool = False
    ack_no_ssh: bool = False
    ack_no_setup_scripts: bool = False
    ack_no_cloud_init: bool = False
    ack_no_training: bool = False
    ack_no_restart_create_delete: bool = False
    ack_no_ssh_key_create_delete: bool = False
    ack_no_filesystem_create_delete: bool = False
    ack_terminate_owned_instance_required: bool = False
    ack_termination_verification_required: bool = False
    ack_os_shutdown_insufficient: bool = False
    ack_no_automatic_launch_retry: bool = False
    ack_operator_present: bool = False
    approval_complete_for_m039_review: bool = False
    approval_passed: bool = False
    missing_acknowledgements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostOperatorApproval:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost operator approval cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_operator_approval_template(
    *,
    acknowledge_all: bool = False,
    approve_future_m039: bool | None = None,
    operator_name: str | None = None,
) -> LambdaLowerCostOperatorApproval:
    if approve_future_m039 is None:
        approve_future_m039 = acknowledge_all
    values = {field: acknowledge_all for field in _ACK_FIELDS}
    missing = [] if acknowledge_all else list(_ACK_FIELDS)
    blockers = [f"missing acknowledgement: {field}" for field in missing]
    if acknowledge_all and not approve_future_m039:
        blockers.append("future M039 lower-cost approval is not explicitly granted")
    if not acknowledge_all or not approve_future_m039:
        blockers.append("operator approval is not marked complete")
    approval_passed = acknowledge_all and approve_future_m039
    return LambdaLowerCostOperatorApproval(
        approval_status=(
            "approved_for_future_m039_lower_cost_launch_attempt"
            if approval_passed
            else "pending_acknowledgement"
        ),
        operator_name=operator_name,
        **values,
        approval_complete_for_m039_review=approval_passed,
        approval_passed=approval_passed,
        missing_acknowledgements=missing,
        blockers=blockers,
        warnings=[
            "operator approval authorizes future M039 review only, not launch now"
        ],
    )


def load_lambda_lower_cost_operator_approval(
    path: str | Path,
) -> LambdaLowerCostOperatorApproval:
    return LambdaLowerCostOperatorApproval.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_operator_approval(
    path: str | Path,
    report: LambdaLowerCostOperatorApproval,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
