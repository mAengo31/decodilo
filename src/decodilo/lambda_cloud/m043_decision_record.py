"""M043 post-capacity decision record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.alternative_shape_operator_selection import (
    load_lambda_alternative_shape_operator_selection,
)
from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    load_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_followup_report import load_lambda_capacity_followup
from decodilo.lambda_cloud.catalog_candidate_rotation import (
    load_lambda_catalog_candidate_rotation,
)

LambdaM043DecisionStatus = Literal[
    "wait_for_live_availability",
    "authorize_future_catalog_candidate_rotation_review",
    "require_operator_selected_alternative_shape",
    "pause_real_launch_attempts",
    "needs_more_evidence",
]


class LambdaM043DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaM043DecisionStatus
    selected_shape: str | None = None
    selected_region: str | None = None
    estimated_30min_cost: float | None = None
    buffered_30min_cost: float | None = None
    launch_authorized_now: bool = False
    future_review_allowed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM043DecisionRecord:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M043 decision cannot authorize immediate launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m043_decision_record_from_paths(
    *,
    capacity_followup: str | Path,
    rotation_rank: str | Path,
    retry_policy: str | Path,
    operator_selection: str | Path,
) -> LambdaM043DecisionRecord:
    followup = load_lambda_capacity_followup(capacity_followup)
    rotation = load_lambda_catalog_candidate_rotation(rotation_rank)
    retry = load_lambda_capacity_aware_retry_policy(retry_policy)
    selection = load_lambda_alternative_shape_operator_selection(operator_selection)
    blockers = [
        *followup.blockers,
        *rotation.blockers,
        *retry.blockers,
        *selection.blockers,
    ]
    selected_shape = selection.selected_shape
    selected_region = selection.selected_region
    estimated = selection.estimated_30min_cost
    buffered = selection.buffered_30min_cost
    if selection.selection_status == "catalog_candidate_selected_for_future_review":
        status: LambdaM043DecisionStatus = (
            "authorize_future_catalog_candidate_rotation_review"
        )
    elif selection.selection_status == "manual_shape_selected_for_future_review":
        status = "require_operator_selected_alternative_shape"
    elif selection.selection_status == "wait_selected":
        status = "wait_for_live_availability"
    elif selection.selection_status == "pause_selected":
        status = "pause_real_launch_attempts"
    elif (
        followup.repeated_capacity_error_detected
        and rotation.selected_candidate is not None
        and not blockers
    ):
        status = "authorize_future_catalog_candidate_rotation_review"
        selected_shape = rotation.selected_candidate.shape
        selected_region = rotation.selected_candidate.region
        estimated = rotation.selected_candidate.estimated_30min_cost
        buffered = rotation.selected_candidate.buffered_estimated_30min_cost
    else:
        status = "wait_for_live_availability" if not blockers else "needs_more_evidence"
    future_allowed = status in {
        "authorize_future_catalog_candidate_rotation_review",
        "require_operator_selected_alternative_shape",
    } and not blockers
    return LambdaM043DecisionRecord(
        decision_status=status if not blockers else "needs_more_evidence",
        selected_shape=selected_shape if not blockers else None,
        selected_region=selected_region if not blockers else None,
        estimated_30min_cost=estimated if not blockers else None,
        buffered_30min_cost=buffered if not blockers else None,
        future_review_allowed=future_allowed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M043 decision is future-review only",
            "no immediate launch is authorized",
        ],
    )


def load_lambda_m043_decision_record(path: str | Path) -> LambdaM043DecisionRecord:
    return LambdaM043DecisionRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m043_decision_record(
    path: str | Path,
    report: LambdaM043DecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
