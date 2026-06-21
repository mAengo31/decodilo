"""M033 combined third-attempt authorization review report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    LambdaEndpointSpecOperatorConfirmationReport,
    load_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.launch_timeout_policy import (
    LambdaLaunchTimeoutPolicy,
    load_lambda_launch_timeout_policy,
)
from decodilo.lambda_cloud.response_capture_settings_lock import (
    LambdaResponseCaptureSettingsLock,
    load_lambda_response_capture_settings_lock,
)
from decodilo.lambda_cloud.third_attempt_authorization import (
    LambdaThirdAttemptAuthorization,
    load_lambda_third_attempt_authorization,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    LambdaThirdAttemptCorrelationPlan,
    load_lambda_third_attempt_correlation_plan,
)
from decodilo.lambda_cloud.third_attempt_go_no_go import (
    LambdaThirdAttemptGoNoGoRecord,
    load_lambda_third_attempt_go_no_go,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    LambdaThirdAttemptReconciliationPlan,
    load_lambda_third_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import (
    LambdaThirdAttemptRiskReview,
    load_lambda_third_attempt_risk_review,
)


class LambdaM033Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-third-attempt-review-m033"
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport
    response_capture_settings_lock: LambdaResponseCaptureSettingsLock
    timeout_policy: LambdaLaunchTimeoutPolicy
    risk_review: LambdaThirdAttemptRiskReview
    correlation_plan: LambdaThirdAttemptCorrelationPlan
    reconciliation_plan: LambdaThirdAttemptReconciliationPlan
    m034_authorization: LambdaThirdAttemptAuthorization
    go_no_go: LambdaThirdAttemptGoNoGoRecord
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM033Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("M033 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m033_report(
    *,
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport,
    response_capture_settings_lock: LambdaResponseCaptureSettingsLock,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    risk_review: LambdaThirdAttemptRiskReview,
    correlation_plan: LambdaThirdAttemptCorrelationPlan,
    reconciliation_plan: LambdaThirdAttemptReconciliationPlan,
    m034_authorization: LambdaThirdAttemptAuthorization,
    go_no_go: LambdaThirdAttemptGoNoGoRecord,
) -> LambdaM033Report:
    blockers = [
        *endpoint_confirmation.blockers,
        *response_capture_settings_lock.blockers,
        *timeout_policy.blockers,
        *risk_review.blockers,
        *correlation_plan.blockers,
        *reconciliation_plan.blockers,
        *m034_authorization.blockers,
        *go_no_go.blockers,
    ]
    return LambdaM033Report(
        endpoint_confirmation=endpoint_confirmation,
        response_capture_settings_lock=response_capture_settings_lock,
        timeout_policy=timeout_policy,
        risk_review=risk_review,
        correlation_plan=correlation_plan,
        reconciliation_plan=reconciliation_plan,
        m034_authorization=m034_authorization,
        go_no_go=go_no_go,
        report_passed=(
            endpoint_confirmation.confirmation_passed
            and response_capture_settings_lock.lock_passed
            and timeout_policy.policy_passed
            and risk_review.third_attempt_risk_passed
            and correlation_plan.plan_passed
            and reconciliation_plan.plan_passed
            and m034_authorization.status
            == "authorized_for_future_m034_third_launch_attempt"
            and go_no_go.status == "go_for_future_m034_third_launch_review"
        ),
        blockers=blockers,
        warnings=["M033 report authorizes only future M034 review, not execution"],
    )


def build_lambda_m033_report_from_paths(
    *,
    endpoint_confirmation: str | Path,
    response_capture_settings_lock: str | Path,
    timeout_policy: str | Path,
    risk_review: str | Path,
    correlation_plan: str | Path,
    reconciliation_plan: str | Path,
    m034_authorization: str | Path,
    go_no_go: str | Path,
) -> LambdaM033Report:
    return build_lambda_m033_report(
        endpoint_confirmation=load_lambda_endpoint_spec_operator_confirmation(
            endpoint_confirmation
        ),
        response_capture_settings_lock=load_lambda_response_capture_settings_lock(
            response_capture_settings_lock
        ),
        timeout_policy=load_lambda_launch_timeout_policy(timeout_policy),
        risk_review=load_lambda_third_attempt_risk_review(risk_review),
        correlation_plan=load_lambda_third_attempt_correlation_plan(correlation_plan),
        reconciliation_plan=load_lambda_third_attempt_reconciliation_plan(
            reconciliation_plan
        ),
        m034_authorization=load_lambda_third_attempt_authorization(m034_authorization),
        go_no_go=load_lambda_third_attempt_go_no_go(go_no_go),
    )


def load_lambda_m033_report(path: str | Path) -> LambdaM033Report:
    return LambdaM033Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m033_report(path: str | Path, report: LambdaM033Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
