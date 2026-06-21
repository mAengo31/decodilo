"""Third-attempt risk review after repeated launch response loss."""

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
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m031_incident_closeout import LambdaM031IncidentCloseoutReport
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    LambdaResponseLossMitigationAcceptanceReport,
    load_lambda_response_loss_mitigation_acceptance,
)


class LambdaThirdAttemptRiskReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prior_attempts_analyzed: int = 2
    prior_response_losses: int
    both_incidents_closed: bool
    mitigation_accepted: bool
    endpoint_confirmation_status: str
    timeout_policy_status: str
    third_attempt_risk_passed: bool
    residual_risk: str = "medium"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptRiskReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("third-attempt risk review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_risk_review(
    *,
    m029c_report: LambdaM029Report,
    m031_report: LambdaM029Report,
    m031d_closeout: LambdaM031IncidentCloseoutReport,
    mitigation_acceptance: LambdaResponseLossMitigationAcceptanceReport,
    endpoint_confirmation: LambdaEndpointSpecOperatorConfirmationReport,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    m029c_incident_closed: bool = True,
) -> LambdaThirdAttemptRiskReview:
    response_losses = sum(
        int(report.launch_request_sent and not report.launch_response_received)
        for report in [m029c_report, m031_report]
    )
    both_closed = bool(m029c_incident_closed and m031d_closeout.closeout_succeeded)
    blockers: list[str] = []
    if not both_closed:
        blockers.append("prior_incident_not_closed")
    if not mitigation_acceptance.mitigation_accepted:
        blockers.append("m032_mitigation_not_accepted")
    if not endpoint_confirmation.confirmation_passed:
        blockers.append("endpoint_confirmation_missing")
    if not timeout_policy.policy_passed:
        blockers.append("timeout_policy_failed")
    if response_losses < 2:
        blockers.append("expected_two_prior_response_losses_missing")
    return LambdaThirdAttemptRiskReview(
        prior_response_losses=response_losses,
        both_incidents_closed=both_closed,
        mitigation_accepted=mitigation_acceptance.mitigation_accepted,
        endpoint_confirmation_status=endpoint_confirmation.confirmation.confirmation_status,
        timeout_policy_status="passed" if timeout_policy.policy_passed else "blocked",
        third_attempt_risk_passed=not blockers,
        blockers=blockers,
        warnings=[
            "two prior launch responses were lost; third attempt requires capture lock "
            "and no retry",
            *endpoint_confirmation.warnings,
            *timeout_policy.warnings,
        ],
    )


def build_lambda_third_attempt_risk_review_from_paths(
    *,
    m029c_report: str | Path,
    m031_report: str | Path,
    m031d_closeout: str | Path,
    mitigation_acceptance: str | Path,
    endpoint_confirmation: str | Path,
    timeout_policy: str | Path,
) -> LambdaThirdAttemptRiskReview:
    return build_lambda_third_attempt_risk_review(
        m029c_report=load_lambda_m029_report(m029c_report),
        m031_report=load_lambda_m029_report(m031_report),
        m031d_closeout=LambdaM031IncidentCloseoutReport.model_validate_json(
            Path(m031d_closeout).read_text(encoding="utf-8")
        ),
        mitigation_acceptance=load_lambda_response_loss_mitigation_acceptance(
            mitigation_acceptance
        ),
        endpoint_confirmation=load_lambda_endpoint_spec_operator_confirmation(
            endpoint_confirmation
        ),
        timeout_policy=load_lambda_launch_timeout_policy(timeout_policy),
    )


def load_lambda_third_attempt_risk_review(path: str | Path) -> LambdaThirdAttemptRiskReview:
    return LambdaThirdAttemptRiskReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_risk_review(
    path: str | Path,
    report: LambdaThirdAttemptRiskReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
