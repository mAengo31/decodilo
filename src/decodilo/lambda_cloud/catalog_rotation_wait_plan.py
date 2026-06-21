"""Wait-for-live-availability plan for declined catalog rotation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_rotation_operator_decision import (
    load_lambda_catalog_rotation_operator_decision,
)

LambdaCatalogRotationWaitPlanStatus = Literal[
    "wait_for_live_availability",
    "not_applicable",
    "blocked",
]


class LambdaCatalogRotationWaitPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan_status: LambdaCatalogRotationWaitPlanStatus
    read_only_discovery_only_when_operator_requested: bool = True
    wait_for_live_availability_evidence: bool = True
    catalog_evidence_only_is_not_live_availability: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogRotationWaitPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog-rotation wait plan cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_rotation_wait_plan_from_path(
    operator_decision: str | Path,
) -> LambdaCatalogRotationWaitPlan:
    decision = load_lambda_catalog_rotation_operator_decision(operator_decision)
    if decision.decision_status == "wait_for_live_availability":
        return LambdaCatalogRotationWaitPlan(
            plan_status="wait_for_live_availability",
            warnings=[
                "wait plan permits read-only discovery only when requested",
                "no launch or mutation is authorized",
            ],
        )
    if decision.decision_status == "incomplete":
        return LambdaCatalogRotationWaitPlan(
            plan_status="blocked",
            blockers=decision.blockers or ["operator_decision_incomplete"],
            warnings=["wait plan blocked until operator chooses wait"],
        )
    return LambdaCatalogRotationWaitPlan(
        plan_status="not_applicable",
        warnings=["operator did not choose wait-for-live-availability path"],
    )


def load_lambda_catalog_rotation_wait_plan(path: str | Path) -> LambdaCatalogRotationWaitPlan:
    return LambdaCatalogRotationWaitPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_wait_plan(
    path: str | Path,
    report: LambdaCatalogRotationWaitPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
