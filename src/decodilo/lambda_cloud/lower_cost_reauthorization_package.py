"""M037 lower-cost shape reauthorization package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_shape_operator_selection import (
    LambdaLowerCostShapeOperatorSelection,
    load_lambda_lower_cost_shape_operator_selection,
)
from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    LambdaLowerCostShapeReauthorization,
    load_lambda_lower_cost_shape_reauthorization,
)

LambdaLowerCostReauthorizationPackageStatus = Literal[
    "not_required",
    "reauthorization_required",
    "ready_for_future_reauthorization",
]


class LambdaLowerCostReauthorizationPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_shape: str | None = None
    selected_gpu_type: str | None = None
    selected_gpus_per_instance: int | None = None
    selected_region: str = "us-west-1"
    estimated_30min_cost: float | None = None
    current_shape_cost: float | None = None
    savings_estimate: float | None = None
    required_regeneration_steps: list[str] = Field(default_factory=list)
    package_status: LambdaLowerCostReauthorizationPackageStatus
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostReauthorizationPackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost reauthorization package cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_reauthorization_package(
    *,
    selection: LambdaLowerCostShapeOperatorSelection,
    lower_cost_review: LambdaLowerCostShapeReauthorization | None = None,
    selected_region: str = "us-west-1",
) -> LambdaLowerCostReauthorizationPackage:
    if selection.selection_status != "select_lower_cost_shape":
        return LambdaLowerCostReauthorizationPackage(
            selected_shape=selection.selected_shape,
            selected_region=selected_region,
            package_status="not_required",
            blockers=selection.blockers,
        )
    candidate = None
    if lower_cost_review is not None:
        candidate = next(
            (
                item
                for item in lower_cost_review.candidates
                if item.shape == selection.selected_shape
            ),
            None,
        )
    current_cost = (
        None
        if lower_cost_review is None
        else lower_cost_review.current_shape_estimated_30min_cost
    )
    estimated = None if candidate is None else candidate.estimated_30min_cost
    return LambdaLowerCostReauthorizationPackage(
        selected_shape=selection.selected_shape,
        selected_gpu_type=None if candidate is None else candidate.gpu_type,
        selected_gpus_per_instance=None if candidate is None else candidate.gpus_per_instance,
        selected_region=selected_region,
        estimated_30min_cost=estimated,
        current_shape_cost=current_cost,
        savings_estimate=None
        if current_cost is None or estimated is None
        else round(current_cost - estimated, 8),
        required_regeneration_steps=[
            "regenerate M020 readiness report for selected lower-cost shape",
            "regenerate M028 report for selected lower-cost shape",
            "regenerate M029 authorization for selected lower-cost shape",
            "regenerate downstream launch strategy artifacts before any future launch",
        ],
        package_status="reauthorization_required",
    )


def build_lambda_lower_cost_reauthorization_package_from_paths(
    *,
    selection: str | Path,
    lower_cost_review: str | Path | None = None,
    selected_region: str = "us-west-1",
) -> LambdaLowerCostReauthorizationPackage:
    return build_lambda_lower_cost_reauthorization_package(
        selection=load_lambda_lower_cost_shape_operator_selection(selection),
        lower_cost_review=None
        if lower_cost_review is None
        else load_lambda_lower_cost_shape_reauthorization(lower_cost_review),
        selected_region=selected_region,
    )


def load_lambda_lower_cost_reauthorization_package(
    path: str | Path,
) -> LambdaLowerCostReauthorizationPackage:
    return LambdaLowerCostReauthorizationPackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_reauthorization_package(
    path: str | Path,
    package: LambdaLowerCostReauthorizationPackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
