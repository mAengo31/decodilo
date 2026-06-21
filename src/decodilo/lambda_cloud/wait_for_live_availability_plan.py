"""Wait plan for operators who decline catalog-only availability risk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_availability_operator_decision import (
    LambdaCatalogAvailabilityOperatorDecision,
    load_lambda_catalog_availability_operator_decision,
)

LambdaWaitForLiveAvailabilityPlanStatus = Literal[
    "wait_for_live_availability",
    "not_applicable",
    "blocked",
]


class LambdaWaitForLiveAvailabilityPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan_status: LambdaWaitForLiveAvailabilityPlanStatus
    periodic_read_only_discovery_only_on_operator_request: bool = True
    product_catalog_is_catalog_evidence_only: bool = True
    no_mutation: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_wait_only(self) -> LambdaWaitForLiveAvailabilityPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_mutation
        ):
            raise ValueError("wait-for-live-availability plan cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_wait_for_live_availability_plan(
    operator_decision: LambdaCatalogAvailabilityOperatorDecision,
) -> LambdaWaitForLiveAvailabilityPlan:
    if operator_decision.decision_status == "wait_for_live_availability":
        status: LambdaWaitForLiveAvailabilityPlanStatus = "wait_for_live_availability"
        blockers: list[str] = []
    elif operator_decision.decision_status == "incomplete":
        status = "blocked"
        blockers = operator_decision.blockers or ["operator_decision_incomplete"]
    else:
        status = "not_applicable"
        blockers = ["operator_accepted_catalog_availability_risk"]
    return LambdaWaitForLiveAvailabilityPlan(
        plan_status=status,
        blockers=blockers,
        warnings=[
            "wait plan permits read-only discovery only when the operator requests it",
            "no launch or mutation is authorized",
        ],
    )


def build_lambda_wait_for_live_availability_plan_from_path(
    operator_decision: str | Path,
) -> LambdaWaitForLiveAvailabilityPlan:
    return build_lambda_wait_for_live_availability_plan(
        load_lambda_catalog_availability_operator_decision(operator_decision)
    )


def load_lambda_wait_for_live_availability_plan(
    path: str | Path,
) -> LambdaWaitForLiveAvailabilityPlan:
    return LambdaWaitForLiveAvailabilityPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_wait_for_live_availability_plan(
    path: str | Path,
    report: LambdaWaitForLiveAvailabilityPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
