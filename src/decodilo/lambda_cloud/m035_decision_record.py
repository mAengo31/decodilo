"""M035 post-incident launch strategy decision record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.fourth_attempt_option_matrix import (
    LambdaFourthAttemptOptionMatrix,
    load_lambda_fourth_attempt_option_matrix,
)

LambdaM035DecisionStatus = Literal[
    "no_go_pause_launches",
    "require_support_confirmation_before_next_launch",
    "authorize_future_m036_fourth_attempt_same_shape",
    "authorize_future_m036_lower_cost_shape_reauthorization",
    "needs_more_evidence",
]


class LambdaM035DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_id: str = "lambda-m035-post-incident-launch-strategy"
    status: LambdaM035DecisionStatus
    recommended_option: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_steps: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM035DecisionRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m035_decision_record(
    option_matrix: LambdaFourthAttemptOptionMatrix,
    *,
    operator_explicitly_accepts_medium_endpoint_risk: bool = False,
    operator_prefers_current_shape: bool = False,
) -> LambdaM035DecisionRecord:
    blockers: list[str] = []
    if option_matrix.risk_review.blockers:
        blockers.extend(option_matrix.risk_review.blockers)
    if option_matrix.endpoint_support_confirmation_required and not (
        operator_explicitly_accepts_medium_endpoint_risk
    ):
        status: LambdaM035DecisionStatus = (
            "require_support_confirmation_before_next_launch"
        )
        steps = [
            "request Lambda support/operator confirmation of launch endpoint behavior",
            "record launch response schema and idempotency guidance",
        ]
    elif (
        option_matrix.lower_cost_shape_reauthorization_required
        and not operator_prefers_current_shape
    ):
        status = "authorize_future_m036_lower_cost_shape_reauthorization"
        steps = [
            "select lower-cost catalog shape",
            "regenerate M020/M028/M029 authorization artifacts for the selected shape",
        ]
    elif operator_explicitly_accepts_medium_endpoint_risk:
        status = "authorize_future_m036_fourth_attempt_same_shape"
        steps = [
            "create a future M036 authorization package",
            "require fresh operator approval before any launch attempt",
        ]
    elif blockers:
        status = "needs_more_evidence"
        steps = ["resolve M035 blockers before any future launch review"]
    else:
        status = "no_go_pause_launches"
        steps = ["pause real launch attempts and continue local/offline work"]
    return LambdaM035DecisionRecord(
        status=status,
        recommended_option=option_matrix.recommended_option,
        blockers=blockers,
        warnings=[
            "M035 authorizes only a future milestone decision path, not execution",
            *option_matrix.warnings,
        ],
        next_required_steps=steps,
    )


def build_lambda_m035_decision_record_from_path(
    option_matrix: str | Path,
) -> LambdaM035DecisionRecord:
    return build_lambda_m035_decision_record(
        load_lambda_fourth_attempt_option_matrix(option_matrix)
    )


def load_lambda_m035_decision_record(path: str | Path) -> LambdaM035DecisionRecord:
    return LambdaM035DecisionRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m035_decision_record(
    path: str | Path,
    record: LambdaM035DecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
