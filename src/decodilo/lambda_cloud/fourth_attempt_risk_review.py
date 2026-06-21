"""M035 fourth-attempt risk review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_attempt_history import (
    LambdaLaunchAttemptHistoryReport,
    load_lambda_launch_attempt_history_report,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    LambdaLaunchEndpointConfidenceReview,
    load_lambda_launch_endpoint_confidence_review,
)


class LambdaFourthAttemptRiskReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prior_attempts_analyzed: int
    prior_response_losses: int
    all_incidents_closed: bool
    crash_safe_diagnostics_required: bool = True
    endpoint_confidence_current: str
    fourth_attempt_risk_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    residual_risk: str = "high"
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFourthAttemptRiskReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 fourth-attempt risk review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_fourth_attempt_risk_review(
    *,
    attempt_history: LambdaLaunchAttemptHistoryReport,
    endpoint_confidence: LambdaLaunchEndpointConfidenceReview,
    crash_safe_diagnostics_accepted: bool = True,
) -> LambdaFourthAttemptRiskReview:
    blockers: list[str] = []
    if not attempt_history.all_incidents_closed:
        blockers.append("all_prior_incidents_must_be_closed")
    if not crash_safe_diagnostics_accepted:
        blockers.append("crash_safe_diagnostics_not_accepted")
    if endpoint_confidence.support_or_docs_confirmation_required:
        blockers.append("endpoint_support_or_docs_confirmation_required")
    return LambdaFourthAttemptRiskReview(
        prior_attempts_analyzed=attempt_history.attempts_represented,
        prior_response_losses=attempt_history.response_loss_count,
        all_incidents_closed=attempt_history.all_incidents_closed,
        endpoint_confidence_current=endpoint_confidence.endpoint_confidence_current,
        fourth_attempt_risk_passed=not blockers,
        blockers=blockers,
        warnings=[
            "a fourth attempt remains high risk after three response-loss outcomes",
            "any future attempt must re-run read-only discovery and operator confirmation",
        ],
    )


def build_lambda_fourth_attempt_risk_review_from_paths(
    *,
    attempt_history: str | Path,
    endpoint_confidence: str | Path,
) -> LambdaFourthAttemptRiskReview:
    return build_lambda_fourth_attempt_risk_review(
        attempt_history=load_lambda_launch_attempt_history_report(attempt_history),
        endpoint_confidence=load_lambda_launch_endpoint_confidence_review(
            endpoint_confidence
        ),
    )


def load_lambda_fourth_attempt_risk_review(
    path: str | Path,
) -> LambdaFourthAttemptRiskReview:
    return LambdaFourthAttemptRiskReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_fourth_attempt_risk_review(
    path: str | Path,
    report: LambdaFourthAttemptRiskReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
