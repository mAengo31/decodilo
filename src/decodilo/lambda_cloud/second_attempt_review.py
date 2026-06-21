"""Combined review status for M030 second-attempt evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    LambdaResponseLossMitigationReview,
)
from decodilo.lambda_cloud.second_attempt_risk_review import LambdaSecondAttemptRiskReport


class LambdaSecondAttemptReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    review_passed: bool
    risk_review_passed: bool
    mitigation_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptReviewReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("second-attempt review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_review(
    *,
    risk_review: LambdaSecondAttemptRiskReport,
    mitigation_review: LambdaResponseLossMitigationReview,
) -> LambdaSecondAttemptReviewReport:
    blockers = [*risk_review.blockers, *mitigation_review.missing_mitigations]
    return LambdaSecondAttemptReviewReport(
        review_passed=risk_review.risk_review_passed and mitigation_review.mitigation_passed,
        risk_review_passed=risk_review.risk_review_passed,
        mitigation_passed=mitigation_review.mitigation_passed,
        blockers=blockers,
        warnings=[
            "Second-attempt review is for future M031 only; no launch in M030",
            *risk_review.warnings,
            *mitigation_review.warnings,
        ],
    )


def load_lambda_second_attempt_review(path: str | Path) -> LambdaSecondAttemptReviewReport:
    return LambdaSecondAttemptReviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_review(
    path: str | Path,
    report: LambdaSecondAttemptReviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
