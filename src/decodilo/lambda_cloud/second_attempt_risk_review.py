"""Second-attempt risk review after the M029C response-loss incident."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    load_lambda_m029_incident_report,
)

RiskLevel = Literal["low", "medium", "high", "critical"]


class LambdaSecondAttemptRiskItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    severity: RiskLevel
    likelihood: RiskLevel
    mitigation: str
    residual_risk: RiskLevel
    blocks_second_attempt: bool = False


class LambdaSecondAttemptRiskReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    risk_review_passed: bool
    incident_closed: bool
    risks: list[LambdaSecondAttemptRiskItem]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaSecondAttemptRiskReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("risk review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_risk_review(
    incident: LambdaM029IncidentReport,
    *,
    mitigation_review_present: bool = True,
) -> LambdaSecondAttemptRiskReport:
    incident_closed = incident.incident_status.startswith("closed_")
    blockers: list[str] = []
    if not incident_closed:
        blockers.append("m029c_incident_not_closed")
    if not mitigation_review_present:
        blockers.append("response_loss_mitigation_review_missing")
    risks = _default_risks(
        incident_closed=incident_closed,
        mitigation_review_present=mitigation_review_present,
    )
    return LambdaSecondAttemptRiskReport(
        risk_review_passed=not blockers,
        incident_closed=incident_closed,
        risks=risks,
        blockers=blockers,
        warnings=[
            "prior response loss requires stricter correlation and reconciliation"
        ],
    )


def _default_risks(
    *,
    incident_closed: bool,
    mitigation_review_present: bool,
) -> list[LambdaSecondAttemptRiskItem]:
    blocking_incident = not incident_closed
    blocking_mitigation = not mitigation_review_present
    return [
        LambdaSecondAttemptRiskItem(
            name="prior launch response lost",
            severity="high",
            likelihood="medium",
            mitigation="record request hash, idempotency key, and post-timeout discovery",
            residual_risk="medium",
            blocks_second_attempt=blocking_mitigation,
        ),
        LambdaSecondAttemptRiskItem(
            name="no owned instance ID recorded",
            severity="high",
            likelihood="medium",
            mitigation="terminate only exact or high-confidence owned candidates",
            residual_risk="medium",
            blocks_second_attempt=blocking_incident,
        ),
        LambdaSecondAttemptRiskItem(
            name="no terminate sent due to missing owned ID",
            severity="medium",
            likelihood="low",
            mitigation="preserve owned-only termination rule",
            residual_risk="low",
        ),
        LambdaSecondAttemptRiskItem(
            name="read-only discovery found no instances",
            severity="low",
            likelihood="low",
            mitigation="require fresh pre-launch discovery before any future attempt",
            residual_risk="low",
        ),
        LambdaSecondAttemptRiskItem(
            name="manual console confirmation found no instances",
            severity="low",
            likelihood="low",
            mitigation="retain console confirmation artifact",
            residual_risk="low",
        ),
        LambdaSecondAttemptRiskItem(
            name="possible provider-side launch failure",
            severity="medium",
            likelihood="medium",
            mitigation="treat launch response loss as ambiguous until reconciled",
            residual_risk="medium",
        ),
        LambdaSecondAttemptRiskItem(
            name="possible launch succeeded then instance disappeared before discovery",
            severity="high",
            likelihood="low",
            mitigation="run immediate post-timeout discovery and console review",
            residual_risk="medium",
        ),
        LambdaSecondAttemptRiskItem(
            name="possible API shape/response issue",
            severity="medium",
            likelihood="medium",
            mitigation="harden response parser and capture raw redacted response shape",
            residual_risk="medium",
        ),
        LambdaSecondAttemptRiskItem(
            name="live availability unknown until launch",
            severity="medium",
            likelihood="medium",
            mitigation="keep one-instance budget/runtime cap and no retry policy",
            residual_risk="medium",
        ),
        LambdaSecondAttemptRiskItem(
            name="repeated response loss risk",
            severity="high",
            likelihood="medium",
            mitigation="new idempotency key plus no automatic retry",
            residual_risk="medium",
            blocks_second_attempt=blocking_mitigation,
        ),
        LambdaSecondAttemptRiskItem(
            name="accidental duplicate launch risk",
            severity="critical",
            likelihood="low",
            mitigation="new deterministic key and explicit no-retry-on-timeout rule",
            residual_risk="medium",
            blocks_second_attempt=blocking_mitigation,
        ),
        LambdaSecondAttemptRiskItem(
            name="termination uncertainty risk",
            severity="critical",
            likelihood="low",
            mitigation="terminate only exact/high-confidence owned instance",
            residual_risk="medium",
            blocks_second_attempt=blocking_incident,
        ),
    ]


def build_lambda_second_attempt_risk_review_from_path(
    incident_report: str | Path,
) -> LambdaSecondAttemptRiskReport:
    return build_lambda_second_attempt_risk_review(
        load_lambda_m029_incident_report(incident_report)
    )


def load_lambda_second_attempt_risk_report(path: str | Path) -> LambdaSecondAttemptRiskReport:
    return LambdaSecondAttemptRiskReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_risk_report(
    path: str | Path,
    report: LambdaSecondAttemptRiskReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
