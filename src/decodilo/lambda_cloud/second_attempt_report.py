"""M030 combined second-attempt review report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    LambdaResponseLossMitigationReview,
)
from decodilo.lambda_cloud.second_attempt_authorization import (
    LambdaSecondAttemptAuthorization,
)
from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    LambdaSecondAttemptCorrelationPlan,
)
from decodilo.lambda_cloud.second_attempt_go_no_go import LambdaSecondAttemptGoNoGoRecord
from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    LambdaSecondAttemptReconciliationPlan,
)
from decodilo.lambda_cloud.second_attempt_risk_review import LambdaSecondAttemptRiskReport


class LambdaSecondAttemptReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-second-attempt-review-m030"
    risk_review: LambdaSecondAttemptRiskReport
    mitigation_review: LambdaResponseLossMitigationReview
    correlation_plan: LambdaSecondAttemptCorrelationPlan
    reconciliation_plan: LambdaSecondAttemptReconciliationPlan
    authorization: LambdaSecondAttemptAuthorization
    go_no_go: LambdaSecondAttemptGoNoGoRecord
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptReport:
        if self.launch_ready or self.launch_allowed or self.real_mutation_enabled:
            raise ValueError("M030 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_report(
    *,
    risk_review: LambdaSecondAttemptRiskReport,
    mitigation_review: LambdaResponseLossMitigationReview,
    correlation_plan: LambdaSecondAttemptCorrelationPlan,
    reconciliation_plan: LambdaSecondAttemptReconciliationPlan,
    authorization: LambdaSecondAttemptAuthorization,
    go_no_go: LambdaSecondAttemptGoNoGoRecord,
) -> LambdaSecondAttemptReport:
    blockers = [
        *risk_review.blockers,
        *mitigation_review.missing_mitigations,
        *correlation_plan.blockers,
        *reconciliation_plan.blockers,
        *authorization.blockers,
        *go_no_go.blockers,
    ]
    return LambdaSecondAttemptReport(
        risk_review=risk_review,
        mitigation_review=mitigation_review,
        correlation_plan=correlation_plan,
        reconciliation_plan=reconciliation_plan,
        authorization=authorization,
        go_no_go=go_no_go,
        report_passed=(
            risk_review.risk_review_passed
            and mitigation_review.mitigation_passed
            and correlation_plan.plan_passed
            and reconciliation_plan.plan_passed
            and authorization.status
            == "authorized_for_future_m031_second_launch_attempt"
            and go_no_go.status == "go_for_future_m031_second_launch_review"
        ),
        blockers=blockers,
        warnings=["M030 report authorizes only future M031 review, not execution"],
    )


def load_lambda_second_attempt_report(path: str | Path) -> LambdaSecondAttemptReport:
    return LambdaSecondAttemptReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_report(
    path: str | Path,
    report: LambdaSecondAttemptReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
