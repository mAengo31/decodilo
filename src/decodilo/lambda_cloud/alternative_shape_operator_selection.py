"""Operator selection for post-capacity alternative Lambda shape strategy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_candidate_rotation import (
    load_lambda_catalog_candidate_rotation,
)
from decodilo.pricing.snapshots import load_price_snapshot

LambdaAlternativeShapeChoice = Literal[
    "wait_for_live_availability",
    "use_selected_catalog_candidate",
    "manually_select_shape",
    "pause_launch_attempts",
]
LambdaAlternativeShapeSelectionStatus = Literal[
    "selection_incomplete",
    "wait_selected",
    "catalog_candidate_selected_for_future_review",
    "manual_shape_selected_for_future_review",
    "pause_selected",
]


class LambdaAlternativeShapeOperatorSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    choice: LambdaAlternativeShapeChoice | None = None
    selection_status: LambdaAlternativeShapeSelectionStatus
    selected_shape: str | None = None
    selected_region: str | None = None
    estimated_30min_cost: float | None = None
    buffered_30min_cost: float | None = None
    operator_risk_acceptance_required: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAlternativeShapeOperatorSelection:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("alternative shape selection cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_alternative_shape_operator_selection_from_paths(
    *,
    rotation_rank: str | Path,
    choose_catalog_candidate: bool = False,
    wait_for_live_availability: bool = False,
    pause_launch_attempts: bool = False,
    manual_shape: str | None = None,
    price_snapshot: str | Path | None = None,
) -> LambdaAlternativeShapeOperatorSelection:
    choices = [
        choose_catalog_candidate,
        wait_for_live_availability,
        pause_launch_attempts,
        manual_shape is not None,
    ]
    blockers: list[str] = []
    if sum(1 for choice in choices if choice) != 1:
        blockers.append("exactly_one_operator_selection_required")
    rotation = load_lambda_catalog_candidate_rotation(rotation_rank)
    selected_shape = None
    selected_region = None
    estimated = None
    buffered = None
    status: LambdaAlternativeShapeSelectionStatus = "selection_incomplete"
    choice_value: LambdaAlternativeShapeChoice | None = None
    risk_required = False
    if choose_catalog_candidate:
        choice_value = "use_selected_catalog_candidate"
        if rotation.selected_candidate is None:
            blockers.extend(rotation.blockers or ["catalog_rotation_has_no_candidate"])
        else:
            selected_shape = rotation.selected_candidate.shape
            selected_region = rotation.selected_candidate.region
            estimated = rotation.selected_candidate.estimated_30min_cost
            buffered = rotation.selected_candidate.buffered_estimated_30min_cost
            risk_required = True
            status = "catalog_candidate_selected_for_future_review"
    elif wait_for_live_availability:
        choice_value = "wait_for_live_availability"
        status = "wait_selected"
    elif pause_launch_attempts:
        choice_value = "pause_launch_attempts"
        status = "pause_selected"
    elif manual_shape is not None:
        choice_value = "manually_select_shape"
        if price_snapshot is None:
            blockers.append("manual_shape_requires_price_snapshot")
        else:
            snapshot = load_price_snapshot(price_snapshot)
            match = next(
                (
                    record
                    for record in snapshot.records
                    if record.provider == "lambda" and record.instance_type == manual_shape
                ),
                None,
            )
            if match is None or snapshot.is_sample_data:
                blockers.append("manual_shape_missing_non_sample_catalog_price")
            else:
                selected_shape = match.instance_type
                selected_region = match.region or "us-west-1"
                estimated = round(match.price_per_instance_hour * 0.5, 8)
                buffered = round(estimated * 1.15, 8)
                risk_required = True
                status = "manual_shape_selected_for_future_review"
    if blockers:
        status = "selection_incomplete"
    return LambdaAlternativeShapeOperatorSelection(
        choice=choice_value,
        selection_status=status,
        selected_shape=selected_shape,
        selected_region=selected_region,
        estimated_30min_cost=estimated,
        buffered_30min_cost=buffered,
        operator_risk_acceptance_required=risk_required,
        blockers=sorted(set(blockers)),
        warnings=[
            "alternative shape selection is future-review only",
            "selection does not authorize immediate launch",
        ],
    )


def load_lambda_alternative_shape_operator_selection(
    path: str | Path,
) -> LambdaAlternativeShapeOperatorSelection:
    return LambdaAlternativeShapeOperatorSelection.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_alternative_shape_operator_selection(
    path: str | Path,
    report: LambdaAlternativeShapeOperatorSelection,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
