"""M035 combined post-incident launch strategy report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.fourth_attempt_option_matrix import (
    LambdaFourthAttemptOptionMatrix,
    load_lambda_fourth_attempt_option_matrix,
)
from decodilo.lambda_cloud.launch_attempt_history import (
    LambdaLaunchAttemptHistoryReport,
    load_lambda_launch_attempt_history_report,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    LambdaLaunchEndpointConfidenceReview,
    load_lambda_launch_endpoint_confidence_review,
)
from decodilo.lambda_cloud.launch_shape_strategy_review import (
    LambdaLaunchShapeStrategyReview,
    load_lambda_launch_shape_strategy_review,
)
from decodilo.lambda_cloud.m035_decision_record import (
    LambdaM035DecisionRecord,
    load_lambda_m035_decision_record,
)
from decodilo.lambda_cloud.support_evidence_request import (
    LambdaSupportEvidenceRequestReport,
    load_lambda_support_evidence_request_report,
)


class LambdaM035Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m035-post-incident-launch-strategy"
    attempt_history: LambdaLaunchAttemptHistoryReport
    endpoint_confidence_review: LambdaLaunchEndpointConfidenceReview
    shape_strategy_review: LambdaLaunchShapeStrategyReview
    option_matrix: LambdaFourthAttemptOptionMatrix
    support_evidence_request: LambdaSupportEvidenceRequestReport
    decision_record: LambdaM035DecisionRecord
    report_passed: bool
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM035Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m035_report(
    *,
    attempt_history: LambdaLaunchAttemptHistoryReport,
    endpoint_confidence_review: LambdaLaunchEndpointConfidenceReview,
    shape_strategy_review: LambdaLaunchShapeStrategyReview,
    option_matrix: LambdaFourthAttemptOptionMatrix,
    support_evidence_request: LambdaSupportEvidenceRequestReport,
    decision_record: LambdaM035DecisionRecord,
) -> LambdaM035Report:
    blockers = [
        *attempt_history.blockers,
        *endpoint_confidence_review.confidence_blockers,
        *shape_strategy_review.blockers,
        *option_matrix.risk_review.blockers,
        *decision_record.blockers,
    ]
    return LambdaM035Report(
        attempt_history=attempt_history,
        endpoint_confidence_review=endpoint_confidence_review,
        shape_strategy_review=shape_strategy_review,
        option_matrix=option_matrix,
        support_evidence_request=support_evidence_request,
        decision_record=decision_record,
        report_passed=(
            attempt_history.attempts_represented == 3
            and attempt_history.all_incidents_closed
            and support_evidence_request.support_request_generated
            and decision_record.status != "needs_more_evidence"
        ),
        blockers=blockers,
        warnings=[
            "M035 report is review-only and cannot authorize immediate execution",
            *attempt_history.warnings,
            *endpoint_confidence_review.confidence_warnings,
            *shape_strategy_review.warnings,
            *option_matrix.warnings,
            *decision_record.warnings,
        ],
    )


def build_lambda_m035_report_from_paths(
    *,
    attempt_history: str | Path,
    endpoint_confidence: str | Path,
    shape_strategy: str | Path,
    option_matrix: str | Path,
    support_request: str | Path,
    decision: str | Path,
) -> LambdaM035Report:
    return build_lambda_m035_report(
        attempt_history=load_lambda_launch_attempt_history_report(attempt_history),
        endpoint_confidence_review=load_lambda_launch_endpoint_confidence_review(
            endpoint_confidence
        ),
        shape_strategy_review=load_lambda_launch_shape_strategy_review(shape_strategy),
        option_matrix=load_lambda_fourth_attempt_option_matrix(option_matrix),
        support_evidence_request=load_lambda_support_evidence_request_report(
            support_request
        ),
        decision_record=load_lambda_m035_decision_record(decision),
    )


def load_lambda_m035_report(path: str | Path) -> LambdaM035Report:
    return LambdaM035Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m035_report(path: str | Path, report: LambdaM035Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
