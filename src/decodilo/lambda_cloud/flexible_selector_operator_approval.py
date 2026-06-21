"""Operator approval template for flexible availability-first launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaFlexibleSelectorOperatorApprovalStatus = Literal[
    "not_provided",
    "approved_for_future_flexible_selector_launch_review",
    "declined_wait_for_live_availability",
]

_ACK_FIELDS = (
    "understands_selector_may_choose_any_approved_shape",
    "understands_catalog_only_live_availability_not_proven",
    "understands_chosen_shape_reported_after_selection",
    "understands_one_instance_only",
    "understands_max_budget_50",
    "understands_max_runtime_30_minutes",
    "understands_existing_ssh_key_attached_no_ssh",
    "understands_no_setup_cloud_init_or_training",
    "understands_no_restart_create_delete",
    "understands_owned_termination_required_if_created",
    "understands_termination_verified_with_read_only_lambda",
    "understands_no_automatic_launch_retry",
    "understands_os_shutdown_insufficient",
)


class LambdaFlexibleSelectorOperatorApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_status: LambdaFlexibleSelectorOperatorApprovalStatus = "not_provided"
    operator_name: str | None = None
    understands_selector_may_choose_any_approved_shape: bool = False
    understands_catalog_only_live_availability_not_proven: bool = False
    understands_chosen_shape_reported_after_selection: bool = False
    understands_one_instance_only: bool = False
    understands_max_budget_50: bool = False
    understands_max_runtime_30_minutes: bool = False
    understands_existing_ssh_key_attached_no_ssh: bool = False
    understands_no_setup_cloud_init_or_training: bool = False
    understands_no_restart_create_delete: bool = False
    understands_owned_termination_required_if_created: bool = False
    understands_termination_verified_with_read_only_lambda: bool = False
    understands_no_automatic_launch_retry: bool = False
    understands_os_shutdown_insufficient: bool = False
    approval_complete: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFlexibleSelectorOperatorApproval:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("flexible-selector approval cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaFlexibleSelectorOperatorApprovalReport = LambdaFlexibleSelectorOperatorApproval


def build_lambda_flexible_selector_operator_approval(
    *,
    approve_future_review: bool = False,
    decline_wait_for_live_availability: bool = False,
    acknowledge_all: bool = False,
    operator_name: str | None = None,
) -> LambdaFlexibleSelectorOperatorApproval:
    blockers: list[str] = []
    if approve_future_review and decline_wait_for_live_availability:
        blockers.append("exactly_one_flexible_selector_operator_choice_required")
    ack_values = {field: acknowledge_all for field in _ACK_FIELDS}
    status: LambdaFlexibleSelectorOperatorApprovalStatus = "not_provided"
    complete = False
    if approve_future_review and not blockers:
        missing = [field for field, value in ack_values.items() if not value]
        if missing:
            blockers.extend(f"missing_acknowledgement:{field}" for field in missing)
        else:
            status = "approved_for_future_flexible_selector_launch_review"
            complete = True
    elif decline_wait_for_live_availability and not blockers:
        status = "declined_wait_for_live_availability"
        complete = True
    elif not blockers:
        blockers.append("flexible_selector_operator_approval_not_provided")
    return LambdaFlexibleSelectorOperatorApproval(
        approval_status=status,
        operator_name=operator_name,
        approval_complete=complete,
        blockers=sorted(set(blockers)),
        warnings=[
            "approval is future-review only",
            "M044G does not authorize immediate launch",
        ],
        **ack_values,
    )


def load_lambda_flexible_selector_operator_approval(
    path: str | Path,
) -> LambdaFlexibleSelectorOperatorApproval:
    return LambdaFlexibleSelectorOperatorApproval.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_flexible_selector_operator_approval(
    path: str | Path,
    report: LambdaFlexibleSelectorOperatorApproval,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
