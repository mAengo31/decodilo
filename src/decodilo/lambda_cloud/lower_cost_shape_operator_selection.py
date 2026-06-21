"""M037 operator selection for lower-cost lifecycle smoke shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    LambdaLowerCostShapeReauthorization,
    load_lambda_lower_cost_shape_reauthorization,
)
from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)

LambdaLowerCostShapeOperatorSelectionStatus = Literal[
    "select_lower_cost_shape",
    "keep_current_shape",
    "needs_operator_selection",
    "lower_cost_shape_not_supported",
]


class LambdaLowerCostShapeOperatorSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selection_status: LambdaLowerCostShapeOperatorSelectionStatus
    selected_shape: str | None = None
    current_shape: str
    operator_selected_shape: str | None = None
    support_confirms_available: bool | None = None
    cost_risk_acceptance_recorded: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostShapeOperatorSelection:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost shape selection cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_shape_operator_selection(
    *,
    lower_cost_review: LambdaLowerCostShapeReauthorization,
    support_response: LambdaSupportConfirmationResponse | None = None,
    operator_selected_shape: str | None = None,
) -> LambdaLowerCostShapeOperatorSelection:
    recommended = lower_cost_review.recommended_candidate
    current_shape = lower_cost_review.current_shape
    if operator_selected_shape == current_shape:
        return LambdaLowerCostShapeOperatorSelection(
            selection_status="keep_current_shape",
            current_shape=current_shape,
            selected_shape=current_shape,
            operator_selected_shape=operator_selected_shape,
            cost_risk_acceptance_recorded=True,
            warnings=["operator selected current higher-cost shape"],
        )
    support_available = _support_availability(support_response)
    target_shape = (
        operator_selected_shape
        or (None if recommended is None else recommended.shape)
        or "gpu_1x_h100_pcie"
    )
    available = support_available.get(target_shape)
    if available is False:
        return LambdaLowerCostShapeOperatorSelection(
            selection_status="lower_cost_shape_not_supported",
            current_shape=current_shape,
            selected_shape=None,
            operator_selected_shape=operator_selected_shape,
            support_confirms_available=False,
            blockers=["lower_cost_shape_not_supported"],
        )
    if available is True and recommended is not None:
        return LambdaLowerCostShapeOperatorSelection(
            selection_status="select_lower_cost_shape",
            current_shape=current_shape,
            selected_shape=target_shape,
            operator_selected_shape=operator_selected_shape,
            support_confirms_available=True,
            warnings=["shape selection requires future reauthorization"],
        )
    return LambdaLowerCostShapeOperatorSelection(
        selection_status="needs_operator_selection",
        current_shape=current_shape,
        selected_shape=None,
        operator_selected_shape=operator_selected_shape,
        support_confirms_available=available,
        blockers=["lower_cost_shape_support_or_operator_selection_missing"],
    )


def build_lambda_lower_cost_shape_operator_selection_from_paths(
    *,
    lower_cost_review: str | Path,
    support_response: str | Path | None = None,
    operator_selected_shape: str | None = None,
) -> LambdaLowerCostShapeOperatorSelection:
    return build_lambda_lower_cost_shape_operator_selection(
        lower_cost_review=load_lambda_lower_cost_shape_reauthorization(
            lower_cost_review
        ),
        support_response=None
        if support_response is None
        else load_lambda_support_confirmation_response(support_response),
        operator_selected_shape=operator_selected_shape,
    )


def _support_availability(
    response: LambdaSupportConfirmationResponse | None,
) -> dict[str, bool]:
    if response is None:
        return {}
    result: dict[str, bool] = {}
    for key in [
        "safe_lifecycle_shape",
        "h100_pcie_1x_supported",
        "lower_cost_non_h100_shape",
    ]:
        answer = response.answer_map().get(key)
        if answer is None:
            continue
        shape = answer.structured_value.get("shape")
        available = answer.structured_value.get("available")
        if shape is not None and isinstance(available, bool):
            result[str(shape)] = available
    return result


def load_lambda_lower_cost_shape_operator_selection(
    path: str | Path,
) -> LambdaLowerCostShapeOperatorSelection:
    return LambdaLowerCostShapeOperatorSelection.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_shape_operator_selection(
    path: str | Path,
    selection: LambdaLowerCostShapeOperatorSelection,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(selection.to_json(), encoding="utf-8")
