"""Combined review status for M033 third-attempt evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    LambdaEndpointSpecOperatorConfirmationReport,
)
from decodilo.lambda_cloud.launch_timeout_policy import LambdaLaunchTimeoutPolicy
from decodilo.lambda_cloud.response_capture_settings_lock import (
    LambdaResponseCaptureSettingsLock,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    LambdaThirdAttemptCorrelationPlan,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    LambdaThirdAttemptReconciliationPlan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import LambdaThirdAttemptRiskReview


class LambdaThirdAttemptReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    review_passed: bool
    endpoint_confirmation_passed: bool
    response_capture_lock_passed: bool
    timeout_policy_passed: bool
    risk_review_passed: bool
    correlation_plan_passed: bool
    reconciliation_plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptReviewReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("third-attempt review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_review(
    *,
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport,
    response_capture_lock: LambdaResponseCaptureSettingsLock,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    risk_review: LambdaThirdAttemptRiskReview,
    correlation_plan: LambdaThirdAttemptCorrelationPlan,
    reconciliation_plan: LambdaThirdAttemptReconciliationPlan,
) -> LambdaThirdAttemptReviewReport:
    blockers = [
        *endpoint_confirmation.blockers,
        *response_capture_lock.blockers,
        *timeout_policy.blockers,
        *risk_review.blockers,
        *correlation_plan.blockers,
        *reconciliation_plan.blockers,
    ]
    return LambdaThirdAttemptReviewReport(
        review_passed=(
            endpoint_confirmation.confirmation_passed
            and response_capture_lock.lock_passed
            and timeout_policy.policy_passed
            and risk_review.third_attempt_risk_passed
            and correlation_plan.plan_passed
            and reconciliation_plan.plan_passed
        ),
        endpoint_confirmation_passed=endpoint_confirmation.confirmation_passed,
        response_capture_lock_passed=response_capture_lock.lock_passed,
        timeout_policy_passed=timeout_policy.policy_passed,
        risk_review_passed=risk_review.third_attempt_risk_passed,
        correlation_plan_passed=correlation_plan.plan_passed,
        reconciliation_plan_passed=reconciliation_plan.plan_passed,
        blockers=blockers,
        warnings=[
            "M033 third-attempt review is for future M034 only; no launch in M033",
            *endpoint_confirmation.warnings,
            *response_capture_lock.warnings,
            *timeout_policy.warnings,
            *risk_review.warnings,
            *correlation_plan.warnings,
            *reconciliation_plan.warnings,
        ],
    )


def load_lambda_third_attempt_review(path: str | Path) -> LambdaThirdAttemptReviewReport:
    return LambdaThirdAttemptReviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_review(
    path: str | Path,
    report: LambdaThirdAttemptReviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
