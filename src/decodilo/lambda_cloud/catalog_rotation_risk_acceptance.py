"""Operator risk acceptance for catalog-rotation Lambda candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_rotation_cost_review import (
    CATALOG_ROTATION_SELECTED_CANDIDATE,
)

LambdaCatalogRotationRiskAcceptanceStatus = Literal[
    "not_provided",
    "accepted_gpu_8x_a100_80gb_sxm4_for_future_review",
    "declined_wait_for_live_availability",
    "declined_choose_manual_candidate",
]

_ACK_FIELDS = (
    "understands_live_availability_not_proven",
    "understands_catalog_backed_not_live_available",
    "understands_prior_h100_pcie_capacity_failure",
    "understands_candidate_larger_than_lifecycle_minimum",
    "understands_m045_may_receive_capacity_error",
    "understands_no_automatic_launch_retry",
    "understands_one_instance_only",
    "understands_max_budget_50",
    "understands_max_runtime_30_minutes",
    "understands_existing_ssh_key_attached_no_ssh",
    "understands_no_setup_cloud_init_or_training",
    "understands_owned_termination_required_if_created",
    "understands_termination_verified_with_read_only_lambda",
    "understands_os_shutdown_insufficient",
)


class LambdaCatalogRotationRiskAcceptance(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str = CATALOG_ROTATION_SELECTED_CANDIDATE
    acceptance_status: LambdaCatalogRotationRiskAcceptanceStatus = "not_provided"
    operator_name: str | None = None
    understands_live_availability_not_proven: bool = False
    understands_catalog_backed_not_live_available: bool = False
    understands_prior_h100_pcie_capacity_failure: bool = False
    understands_candidate_larger_than_lifecycle_minimum: bool = False
    understands_m045_may_receive_capacity_error: bool = False
    understands_no_automatic_launch_retry: bool = False
    understands_one_instance_only: bool = False
    understands_max_budget_50: bool = False
    understands_max_runtime_30_minutes: bool = False
    understands_existing_ssh_key_attached_no_ssh: bool = False
    understands_no_setup_cloud_init_or_training: bool = False
    understands_owned_termination_required_if_created: bool = False
    understands_termination_verified_with_read_only_lambda: bool = False
    understands_os_shutdown_insufficient: bool = False
    acceptance_complete: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaCatalogRotationRiskAcceptance:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog-rotation risk acceptance cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCatalogRotationRiskAcceptanceReport = LambdaCatalogRotationRiskAcceptance


def build_lambda_catalog_rotation_risk_acceptance(
    *,
    accept_selected_candidate: bool = False,
    decline_wait: bool = False,
    decline_manual_selection: bool = False,
    acknowledge_all: bool = False,
    operator_name: str | None = None,
) -> LambdaCatalogRotationRiskAcceptance:
    requested = [accept_selected_candidate, decline_wait, decline_manual_selection]
    blockers: list[str] = []
    if sum(1 for item in requested if item) > 1:
        blockers.append("exactly_one_catalog_rotation_operator_choice_required")
    ack_values = {field: acknowledge_all for field in _ACK_FIELDS}
    status: LambdaCatalogRotationRiskAcceptanceStatus = "not_provided"
    complete = False
    if accept_selected_candidate and not blockers:
        missing = [field for field, value in ack_values.items() if not value]
        if missing:
            blockers.extend(f"missing_acknowledgement:{field}" for field in missing)
            status = "not_provided"
        else:
            status = "accepted_gpu_8x_a100_80gb_sxm4_for_future_review"
            complete = True
    elif decline_wait and not blockers:
        status = "declined_wait_for_live_availability"
        complete = True
    elif decline_manual_selection and not blockers:
        status = "declined_choose_manual_candidate"
        complete = True
    elif not blockers:
        blockers.append("catalog_rotation_operator_decision_not_provided")
    return LambdaCatalogRotationRiskAcceptance(
        acceptance_status=status,
        operator_name=operator_name,
        acceptance_complete=complete,
        blockers=sorted(set(blockers)),
        warnings=[
            "risk acceptance is future-review only",
            "M044 does not authorize immediate launch",
        ],
        **ack_values,
    )


def load_lambda_catalog_rotation_risk_acceptance(
    path: str | Path,
) -> LambdaCatalogRotationRiskAcceptance:
    return LambdaCatalogRotationRiskAcceptance.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_risk_acceptance(
    path: str | Path,
    report: LambdaCatalogRotationRiskAcceptance,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
