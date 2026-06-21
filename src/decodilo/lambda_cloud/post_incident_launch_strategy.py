"""M035 post-incident launch strategy package."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.fourth_attempt_option_matrix import (
    LambdaFourthAttemptOptionMatrix,
)
from decodilo.lambda_cloud.launch_attempt_history import (
    LambdaLaunchAttemptHistoryReport,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    LambdaLaunchEndpointConfidenceReview,
)
from decodilo.lambda_cloud.launch_shape_strategy_review import (
    LambdaLaunchShapeStrategyReview,
)
from decodilo.lambda_cloud.m035_decision_record import LambdaM035DecisionRecord
from decodilo.lambda_cloud.support_evidence_request import (
    LambdaSupportEvidenceRequestReport,
)


class LambdaPostIncidentLaunchStrategy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    strategy_id: str = "lambda-post-incident-launch-strategy-m035"
    attempt_history: LambdaLaunchAttemptHistoryReport
    endpoint_confidence_review: LambdaLaunchEndpointConfidenceReview
    shape_strategy_review: LambdaLaunchShapeStrategyReview
    option_matrix: LambdaFourthAttemptOptionMatrix
    support_evidence_request: LambdaSupportEvidenceRequestReport
    decision_record: LambdaM035DecisionRecord
    strategy_passed: bool
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaPostIncidentLaunchStrategy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 strategy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_post_incident_launch_strategy(
    *,
    attempt_history: LambdaLaunchAttemptHistoryReport,
    endpoint_confidence_review: LambdaLaunchEndpointConfidenceReview,
    shape_strategy_review: LambdaLaunchShapeStrategyReview,
    option_matrix: LambdaFourthAttemptOptionMatrix,
    support_evidence_request: LambdaSupportEvidenceRequestReport,
    decision_record: LambdaM035DecisionRecord,
) -> LambdaPostIncidentLaunchStrategy:
    strategy_passed = (
        attempt_history.attempts_represented == 3
        and attempt_history.all_incidents_closed
        and support_evidence_request.support_request_generated
        and decision_record.status
        in {
            "require_support_confirmation_before_next_launch",
            "authorize_future_m036_fourth_attempt_same_shape",
            "authorize_future_m036_lower_cost_shape_reauthorization",
            "no_go_pause_launches",
        }
    )
    return LambdaPostIncidentLaunchStrategy(
        attempt_history=attempt_history,
        endpoint_confidence_review=endpoint_confidence_review,
        shape_strategy_review=shape_strategy_review,
        option_matrix=option_matrix,
        support_evidence_request=support_evidence_request,
        decision_record=decision_record,
        strategy_passed=strategy_passed,
        warnings=[
            "M035 is a strategy decision only; no launch, mutation, or spend is authorized"
        ],
    )


def load_lambda_post_incident_launch_strategy(
    path: str | Path,
) -> LambdaPostIncidentLaunchStrategy:
    return LambdaPostIncidentLaunchStrategy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_post_incident_launch_strategy(
    path: str | Path,
    report: LambdaPostIncidentLaunchStrategy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
