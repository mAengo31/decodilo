"""Future-M031-only authorization for a second Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    load_lambda_m029_incident_report,
)
from decodilo.lambda_cloud.response_loss_mitigation_review import (
    LambdaResponseLossMitigationReview,
    load_lambda_response_loss_mitigation_review,
)
from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    LambdaSecondAttemptCorrelationPlan,
    load_lambda_second_attempt_correlation_plan,
)
from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    LambdaSecondAttemptReconciliationPlan,
    load_lambda_second_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.second_attempt_risk_review import (
    LambdaSecondAttemptRiskReport,
    load_lambda_second_attempt_risk_report,
)

LambdaSecondAttemptAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m031_second_launch_attempt",
]


class LambdaSecondAttemptAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_id: str = "lambda-second-attempt-authorization-m030"
    status: LambdaSecondAttemptAuthorizationStatus
    incident_status: str
    authorized_for: str = "future_m031_second_launch_attempt"
    authorized_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptAuthorization:
        if self.launch_ready or self.launch_allowed or self.real_mutation_enabled:
            raise ValueError("M030 second-attempt authorization cannot enable launch")
        if self.status not in {
            "not_authorized",
            "authorized_for_future_m031_second_launch_attempt",
        }:
            raise ValueError("forbidden second-attempt authorization status")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_authorization(
    *,
    incident: LambdaM029IncidentReport,
    risk_review: LambdaSecondAttemptRiskReport,
    mitigation_review: LambdaResponseLossMitigationReview,
    correlation_plan: LambdaSecondAttemptCorrelationPlan,
    reconciliation_plan: LambdaSecondAttemptReconciliationPlan,
) -> LambdaSecondAttemptAuthorization:
    blockers: list[str] = []
    if not incident.incident_status.startswith("closed_"):
        blockers.append("m029c_incident_not_closed")
    if not risk_review.risk_review_passed:
        blockers.extend(risk_review.blockers)
    if not mitigation_review.mitigation_passed:
        blockers.extend(mitigation_review.missing_mitigations)
    if not correlation_plan.plan_passed:
        blockers.extend(correlation_plan.blockers)
    if not reconciliation_plan.plan_passed:
        blockers.extend(reconciliation_plan.blockers)
    status: LambdaSecondAttemptAuthorizationStatus = (
        "authorized_for_future_m031_second_launch_attempt"
        if not blockers
        else "not_authorized"
    )
    return LambdaSecondAttemptAuthorization(
        status=status,
        incident_status=incident.incident_status,
        authorized_operations=[
            "future launch_one_instance attempt only",
            "future read-only running verification",
            "future terminate exact/high-confidence owned instance only",
            "future read-only termination verification",
        ],
        forbidden_operations=[
            "launch now",
            "terminate now",
            "restart",
            "create/delete SSH key",
            "create/delete filesystem",
            "SSH",
            "setup scripts",
            "training",
            "background execution",
        ],
        blockers=blockers,
        warnings=["Authorization is for future M031 review only; M030 is non-executing"],
    )


def build_lambda_second_attempt_authorization_from_paths(
    *,
    incident_report: str | Path,
    risk_review: str | Path,
    mitigation_review: str | Path,
    correlation_plan: str | Path,
    reconciliation_plan: str | Path,
) -> LambdaSecondAttemptAuthorization:
    return build_lambda_second_attempt_authorization(
        incident=load_lambda_m029_incident_report(incident_report),
        risk_review=load_lambda_second_attempt_risk_report(risk_review),
        mitigation_review=load_lambda_response_loss_mitigation_review(mitigation_review),
        correlation_plan=load_lambda_second_attempt_correlation_plan(correlation_plan),
        reconciliation_plan=load_lambda_second_attempt_reconciliation_plan(
            reconciliation_plan
        ),
    )


def load_lambda_second_attempt_authorization(
    path: str | Path,
) -> LambdaSecondAttemptAuthorization:
    return LambdaSecondAttemptAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_authorization(
    path: str | Path,
    authorization: LambdaSecondAttemptAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
