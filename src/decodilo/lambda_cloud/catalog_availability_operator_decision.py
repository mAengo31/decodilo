"""Decision derived from catalog-only availability risk acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    LambdaCatalogAvailabilityRiskAcceptanceReport,
    load_lambda_catalog_availability_risk_acceptance,
)

LambdaCatalogAvailabilityOperatorDecisionStatus = Literal[
    "accept_catalog_availability_risk_for_future_m042_review",
    "wait_for_live_availability",
    "incomplete",
]


class LambdaCatalogAvailabilityOperatorDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaCatalogAvailabilityOperatorDecisionStatus
    risk_acceptance_status: str
    future_m042_review_allowed: bool
    wait_for_live_availability: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogAvailabilityOperatorDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog availability decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_availability_operator_decision(
    risk_acceptance: LambdaCatalogAvailabilityRiskAcceptanceReport,
) -> LambdaCatalogAvailabilityOperatorDecision:
    if (
        risk_acceptance.acceptance_status == "accepted_for_future_m042_review"
        and risk_acceptance.acceptance_complete_for_m042_review
    ):
        status: LambdaCatalogAvailabilityOperatorDecisionStatus = (
            "accept_catalog_availability_risk_for_future_m042_review"
        )
        blockers: list[str] = []
    elif risk_acceptance.acceptance_status == "declined_wait_for_live_availability":
        status = "wait_for_live_availability"
        blockers = []
    else:
        status = "incomplete"
        blockers = risk_acceptance.blockers or ["catalog_availability_risk_not_accepted"]
    return LambdaCatalogAvailabilityOperatorDecision(
        decision_status=status,
        risk_acceptance_status=risk_acceptance.acceptance_status,
        future_m042_review_allowed=(
            status == "accept_catalog_availability_risk_for_future_m042_review"
        ),
        wait_for_live_availability=status == "wait_for_live_availability",
        blockers=blockers,
        warnings=[
            "operator decision is future-review only",
            "M041 does not authorize immediate launch",
        ],
    )


def build_lambda_catalog_availability_operator_decision_from_path(
    risk_acceptance: str | Path,
) -> LambdaCatalogAvailabilityOperatorDecision:
    return build_lambda_catalog_availability_operator_decision(
        load_lambda_catalog_availability_risk_acceptance(risk_acceptance)
    )


def load_lambda_catalog_availability_operator_decision(
    path: str | Path,
) -> LambdaCatalogAvailabilityOperatorDecision:
    return LambdaCatalogAvailabilityOperatorDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_availability_operator_decision(
    path: str | Path,
    report: LambdaCatalogAvailabilityOperatorDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
