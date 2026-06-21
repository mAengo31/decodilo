"""Operator risk acceptance for catalog-only Lambda availability evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaCatalogAvailabilityRiskAcceptanceStatus = Literal[
    "not_provided",
    "accepted_for_future_m042_review",
    "declined_wait_for_live_availability",
]

_ACK_FIELDS = [
    "ack_live_availability_not_proven",
    "ack_candidate_catalog_backed_not_live_available",
    "ack_previous_gpu_1x_h100_pcie_capacity_failure",
    "ack_m042_may_receive_another_capacity_error",
    "ack_no_automatic_launch_retry",
    "ack_one_instance_only",
    "ack_max_budget_50",
    "ack_max_runtime_30_min",
    "ack_existing_ssh_key_attached_but_no_ssh",
    "ack_no_setup_scripts_cloud_init_training",
    "ack_owned_instance_termination_required",
    "ack_termination_verified_by_read_only_get_list",
    "ack_os_shutdown_insufficient",
]


class LambdaCatalogAvailabilityRiskAcceptanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    acceptance_id: str = "lambda-catalog-availability-risk-acceptance"
    acceptance_status: LambdaCatalogAvailabilityRiskAcceptanceStatus = "not_provided"
    operator_name: str | None = None
    ack_live_availability_not_proven: bool = False
    ack_candidate_catalog_backed_not_live_available: bool = False
    ack_previous_gpu_1x_h100_pcie_capacity_failure: bool = False
    ack_m042_may_receive_another_capacity_error: bool = False
    ack_no_automatic_launch_retry: bool = False
    ack_one_instance_only: bool = False
    ack_max_budget_50: bool = False
    ack_max_runtime_30_min: bool = False
    ack_existing_ssh_key_attached_but_no_ssh: bool = False
    ack_no_setup_scripts_cloud_init_training: bool = False
    ack_owned_instance_termination_required: bool = False
    ack_termination_verified_by_read_only_get_list: bool = False
    ack_os_shutdown_insufficient: bool = False
    acceptance_complete_for_m042_review: bool = False
    missing_acknowledgements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogAvailabilityRiskAcceptanceReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog availability risk acceptance cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCatalogAvailabilityRiskAcceptance = LambdaCatalogAvailabilityRiskAcceptanceReport


def build_lambda_catalog_availability_risk_acceptance(
    *,
    accept_risk: bool = False,
    decline_risk: bool = False,
    acknowledge_all: bool = False,
    operator_name: str | None = None,
) -> LambdaCatalogAvailabilityRiskAcceptanceReport:
    values = {field: acknowledge_all for field in _ACK_FIELDS}
    blockers: list[str] = []
    warnings = [
        "catalog-only availability acceptance is for future M042 review only",
        "launch_ready and launch_allowed remain false",
    ]
    if accept_risk and decline_risk:
        blockers.append("risk acceptance cannot both accept and decline")
    if decline_risk and not accept_risk:
        return LambdaCatalogAvailabilityRiskAcceptanceReport(
            acceptance_status="declined_wait_for_live_availability",
            operator_name=operator_name,
            blockers=[],
            warnings=[
                "operator declined catalog-only availability risk",
                "wait-for-live-availability plan should be produced",
            ],
        )
    if not accept_risk:
        blockers.append("catalog availability risk decision not provided")
    missing = [field for field, value in values.items() if not value]
    blockers.extend(f"missing acknowledgement: {field}" for field in missing)
    accepted = accept_risk and not blockers
    return LambdaCatalogAvailabilityRiskAcceptanceReport(
        acceptance_status=(
            "accepted_for_future_m042_review" if accepted else "not_provided"
        ),
        operator_name=operator_name,
        **values,
        acceptance_complete_for_m042_review=accepted,
        missing_acknowledgements=missing,
        blockers=blockers,
        warnings=warnings,
    )


def load_lambda_catalog_availability_risk_acceptance(
    path: str | Path,
) -> LambdaCatalogAvailabilityRiskAcceptanceReport:
    return LambdaCatalogAvailabilityRiskAcceptanceReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_availability_risk_acceptance(
    path: str | Path,
    report: LambdaCatalogAvailabilityRiskAcceptanceReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
