"""Future-M034-only authorization gate for a third Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_spec_operator_confirmation import (
    LambdaEndpointSpecOperatorConfirmationReport,
    load_lambda_endpoint_spec_operator_confirmation,
)
from decodilo.lambda_cloud.future_launch_hold_release import (
    LambdaFutureLaunchHoldReleaseReport,
    load_lambda_future_launch_hold_release,
)
from decodilo.lambda_cloud.launch_timeout_policy import (
    LambdaLaunchTimeoutPolicy,
    load_lambda_launch_timeout_policy,
)
from decodilo.lambda_cloud.m031_incident_closeout import LambdaM031IncidentCloseoutReport
from decodilo.lambda_cloud.m034_authorization_record import (
    LambdaM034AuthorizationRecord,
    LambdaM034AuthorizationStatus,
    build_lambda_m034_authorization_record,
)
from decodilo.lambda_cloud.response_capture_settings_lock import (
    LambdaResponseCaptureSettingsLock,
    load_lambda_response_capture_settings_lock,
)
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    LambdaResponseLossMitigationAcceptanceReport,
    load_lambda_response_loss_mitigation_acceptance,
)
from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    LambdaThirdAttemptCorrelationPlan,
    load_lambda_third_attempt_correlation_plan,
)
from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    LambdaThirdAttemptReconciliationPlan,
    load_lambda_third_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.third_attempt_risk_review import (
    LambdaThirdAttemptRiskReview,
    load_lambda_third_attempt_risk_review,
)


class LambdaThirdAttemptAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_id: str = "lambda-third-attempt-authorization-m033"
    status: LambdaM034AuthorizationStatus
    m034_authorization_record: LambdaM034AuthorizationRecord
    incident_status: str
    mitigation_accepted: bool
    future_launch_hold_released_for_review: bool
    renewed_operator_approval_present: bool
    fresh_readonly_discovery_present: bool
    budget_resource_checks_valid: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("M033 third-attempt authorization cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_authorization(
    *,
    m031_closeout: LambdaM031IncidentCloseoutReport,
    mitigation_acceptance: LambdaResponseLossMitigationAcceptanceReport,
    hold_release: LambdaFutureLaunchHoldReleaseReport,
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport,
    response_capture_lock: LambdaResponseCaptureSettingsLock,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    risk_review: LambdaThirdAttemptRiskReview,
    correlation_plan: LambdaThirdAttemptCorrelationPlan,
    reconciliation_plan: LambdaThirdAttemptReconciliationPlan,
    fresh_readonly_discovery_present: bool = True,
    budget_resource_checks_valid: bool = True,
    renewed_operator_approval_present: bool = True,
) -> LambdaThirdAttemptAuthorization:
    blockers: list[str] = []
    if not m031_closeout.closeout_succeeded:
        blockers.append("m031_incident_not_closed")
    if not mitigation_acceptance.mitigation_accepted:
        blockers.append("m032_mitigation_not_accepted")
    if not hold_release.hold_released_for_future_review:
        blockers.append("future_launch_hold_not_released_for_review")
    if not endpoint_confirmation.confirmation_passed:
        blockers.append("endpoint_confirmation_missing")
    if not response_capture_lock.lock_passed:
        blockers.append("response_capture_lock_failed")
    if not timeout_policy.policy_passed:
        blockers.append("timeout_policy_failed")
    if not risk_review.third_attempt_risk_passed:
        blockers.append("third_attempt_risk_review_failed")
    if not correlation_plan.plan_passed:
        blockers.append("third_attempt_correlation_plan_failed")
    if not reconciliation_plan.plan_passed:
        blockers.append("third_attempt_reconciliation_plan_failed")
    if not fresh_readonly_discovery_present:
        blockers.append("fresh_readonly_discovery_missing")
    if not budget_resource_checks_valid:
        blockers.append("budget_resource_checks_invalid")
    if not renewed_operator_approval_present:
        blockers.append("renewed_operator_approval_missing")
    status: LambdaM034AuthorizationStatus = (
        "authorized_for_future_m034_third_launch_attempt"
        if not blockers
        else "not_authorized"
    )
    record = build_lambda_m034_authorization_record(
        status=status,
        blockers=blockers,
        warnings=["M034 requires a fresh operator-supervised run; M033 is review-only"],
    )
    return LambdaThirdAttemptAuthorization(
        status=status,
        m034_authorization_record=record,
        incident_status=m031_closeout.incident_status,
        mitigation_accepted=mitigation_acceptance.mitigation_accepted,
        future_launch_hold_released_for_review=(
            hold_release.hold_released_for_future_review
        ),
        renewed_operator_approval_present=renewed_operator_approval_present,
        fresh_readonly_discovery_present=fresh_readonly_discovery_present,
        budget_resource_checks_valid=budget_resource_checks_valid,
        blockers=blockers,
        warnings=[
            "M034 future-review package is non-executing in M033",
            *mitigation_acceptance.warnings,
            *hold_release.warnings,
            *endpoint_confirmation.warnings,
        ],
    )


def build_lambda_third_attempt_authorization_from_paths(
    *,
    m031_closeout: str | Path,
    mitigation_acceptance: str | Path,
    hold_release: str | Path,
    endpoint_confirmation: str | Path,
    response_capture_lock: str | Path,
    timeout_policy: str | Path,
    risk_review: str | Path,
    correlation_plan: str | Path,
    reconciliation_plan: str | Path,
    fresh_readonly_discovery_present: bool = True,
    budget_resource_checks_valid: bool = True,
    renewed_operator_approval_present: bool = True,
) -> LambdaThirdAttemptAuthorization:
    return build_lambda_third_attempt_authorization(
        m031_closeout=LambdaM031IncidentCloseoutReport.model_validate_json(
            Path(m031_closeout).read_text(encoding="utf-8")
        ),
        mitigation_acceptance=load_lambda_response_loss_mitigation_acceptance(
            mitigation_acceptance
        ),
        hold_release=load_lambda_future_launch_hold_release(hold_release),
        endpoint_confirmation=load_lambda_endpoint_spec_operator_confirmation(
            endpoint_confirmation
        ),
        response_capture_lock=load_lambda_response_capture_settings_lock(
            response_capture_lock
        ),
        timeout_policy=load_lambda_launch_timeout_policy(timeout_policy),
        risk_review=load_lambda_third_attempt_risk_review(risk_review),
        correlation_plan=load_lambda_third_attempt_correlation_plan(correlation_plan),
        reconciliation_plan=load_lambda_third_attempt_reconciliation_plan(
            reconciliation_plan
        ),
        fresh_readonly_discovery_present=fresh_readonly_discovery_present,
        budget_resource_checks_valid=budget_resource_checks_valid,
        renewed_operator_approval_present=renewed_operator_approval_present,
    )


def load_lambda_third_attempt_authorization(
    path: str | Path,
) -> LambdaThirdAttemptAuthorization:
    return LambdaThirdAttemptAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_authorization(
    path: str | Path,
    authorization: LambdaThirdAttemptAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
