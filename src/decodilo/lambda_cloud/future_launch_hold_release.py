"""Review-only release evaluation for the repeated response-loss launch hold."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m031_incident_report import (
    LambdaM031IncidentReport,
    load_lambda_m031_incident_report,
)
from decodilo.lambda_cloud.response_loss_mitigation_acceptance import (
    LambdaResponseLossMitigationAcceptanceReport,
    load_lambda_response_loss_mitigation_acceptance,
)


class LambdaFutureLaunchHoldReleaseReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    future_launch_hold_active: bool
    hold_released_for_future_review: bool
    release_status: str
    hold_reasons: list[str] = Field(default_factory=list)
    required_clearance_items: list[str] = Field(default_factory=list)
    incident_closeout_required: bool
    repeated_response_loss_review_required: bool
    root_cause_mitigation_required: bool
    operator_reapproval_required: bool = True
    launch_authorized: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaFutureLaunchHoldReleaseReport:
        if self.launch_ready or self.launch_allowed or self.launch_authorized:
            raise ValueError("future launch hold release cannot authorize launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_future_launch_hold_release(
    *,
    m031_incident_report: LambdaM031IncidentReport,
    mitigation_acceptance: LambdaResponseLossMitigationAcceptanceReport,
) -> LambdaFutureLaunchHoldReleaseReport:
    incident_closed = m031_incident_report.incident_status.startswith("closed_")
    blockers: list[str] = []
    required: list[str] = []
    if not incident_closed:
        blockers.append("m031_incident_open")
        required.append("close M031 incident")
    if not mitigation_acceptance.mitigation_accepted:
        blockers.append("response_loss_mitigation_not_accepted")
        required.append("accept response-loss mitigation evidence")
    if mitigation_acceptance.endpoint_spec_confidence not in {"medium", "high"}:
        blockers.append("endpoint_spec_confidence_too_low")
        required.append("record medium/high confidence endpoint spec")
    required.append("obtain fresh operator approval before any future launch")
    released = not blockers
    return LambdaFutureLaunchHoldReleaseReport(
        future_launch_hold_active=not released,
        hold_released_for_future_review=released,
        release_status="released_for_future_review" if released else "hold_active",
        hold_reasons=blockers,
        required_clearance_items=required,
        incident_closeout_required=not incident_closed,
        repeated_response_loss_review_required=not mitigation_acceptance.mitigation_accepted,
        root_cause_mitigation_required=not mitigation_acceptance.mitigation_accepted,
        warnings=[
            "hold release clears repeated response-loss blocker for review only; it does not launch"
        ],
    )


def evaluate_lambda_future_launch_hold_release_from_paths(
    *,
    m031_incident_report: str | Path,
    mitigation_acceptance: str | Path,
) -> LambdaFutureLaunchHoldReleaseReport:
    return evaluate_lambda_future_launch_hold_release(
        m031_incident_report=load_lambda_m031_incident_report(m031_incident_report),
        mitigation_acceptance=load_lambda_response_loss_mitigation_acceptance(
            mitigation_acceptance
        ),
    )


def load_lambda_future_launch_hold_release(
    path: str | Path,
) -> LambdaFutureLaunchHoldReleaseReport:
    return LambdaFutureLaunchHoldReleaseReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_future_launch_hold_release(
    path: str | Path,
    report: LambdaFutureLaunchHoldReleaseReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
