"""Derive the M044 operator decision from catalog-rotation risk acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    load_lambda_catalog_rotation_risk_acceptance,
)

LambdaCatalogRotationOperatorDecisionStatus = Literal[
    "accept_selected_catalog_rotation_candidate",
    "wait_for_live_availability",
    "require_manual_candidate_selection",
    "incomplete",
]


class LambdaCatalogRotationOperatorDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaCatalogRotationOperatorDecisionStatus
    selected_candidate: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogRotationOperatorDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog-rotation operator decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_rotation_operator_decision_from_path(
    risk_acceptance: str | Path,
) -> LambdaCatalogRotationOperatorDecision:
    acceptance = load_lambda_catalog_rotation_risk_acceptance(risk_acceptance)
    if (
        acceptance.acceptance_status
        == "accepted_gpu_8x_a100_80gb_sxm4_for_future_review"
    ):
        status: LambdaCatalogRotationOperatorDecisionStatus = (
            "accept_selected_catalog_rotation_candidate"
        )
        selected = acceptance.selected_candidate
        blockers: list[str] = []
    elif acceptance.acceptance_status == "declined_wait_for_live_availability":
        status = "wait_for_live_availability"
        selected = None
        blockers = []
    elif acceptance.acceptance_status == "declined_choose_manual_candidate":
        status = "require_manual_candidate_selection"
        selected = None
        blockers = []
    else:
        status = "incomplete"
        selected = None
        blockers = acceptance.blockers or ["catalog_rotation_operator_decision_incomplete"]
    return LambdaCatalogRotationOperatorDecision(
        decision_status=status,
        selected_candidate=selected,
        blockers=sorted(set(blockers)),
        warnings=[
            "operator decision is review-only",
            "no immediate launch is authorized",
        ],
    )


def load_lambda_catalog_rotation_operator_decision(
    path: str | Path,
) -> LambdaCatalogRotationOperatorDecision:
    return LambdaCatalogRotationOperatorDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_operator_decision(
    path: str | Path,
    report: LambdaCatalogRotationOperatorDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
