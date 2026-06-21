"""Future launch hold after M031 repeated response loss."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m031_incident_report import (
    LambdaM031IncidentReport,
    load_lambda_m031_incident_report,
)
from decodilo.lambda_cloud.repeated_response_loss_review import (
    LambdaRepeatedResponseLossReviewReport,
    load_lambda_repeated_response_loss_review,
)


class LambdaFutureLaunchHoldReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    future_launch_hold_active: bool
    hold_reasons: list[str] = Field(default_factory=list)
    required_clearance_items: list[str] = Field(default_factory=list)
    incident_closeout_required: bool
    repeated_response_loss_review_required: bool
    root_cause_mitigation_required: bool
    operator_reapproval_required: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaFutureLaunchHoldReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("future launch hold cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_future_launch_hold(
    *,
    m031_incident_report: LambdaM031IncidentReport,
    repeated_response_loss_review: LambdaRepeatedResponseLossReviewReport,
) -> LambdaFutureLaunchHoldReport:
    incident_open = not m031_incident_report.incident_status.startswith("closed_")
    repeated_blocked = repeated_response_loss_review.future_launch_blocked
    hold_reasons: list[str] = []
    required: list[str] = []
    if incident_open:
        hold_reasons.append("m031_incident_open")
        required.append("close M031 incident")
    if repeated_blocked:
        hold_reasons.append("repeated_response_loss_unmitigated")
        required.append("complete and accept repeated response-loss mitigation")
    required.append("obtain fresh operator approval for any future launch")
    return LambdaFutureLaunchHoldReport(
        future_launch_hold_active=bool(incident_open or repeated_blocked),
        hold_reasons=hold_reasons,
        required_clearance_items=required,
        incident_closeout_required=incident_open,
        repeated_response_loss_review_required=repeated_blocked,
        root_cause_mitigation_required=repeated_blocked,
    )


def build_lambda_future_launch_hold_from_paths(
    *,
    m031_incident_report: str | Path,
    repeated_response_loss_review: str | Path,
) -> LambdaFutureLaunchHoldReport:
    return build_lambda_future_launch_hold(
        m031_incident_report=load_lambda_m031_incident_report(m031_incident_report),
        repeated_response_loss_review=load_lambda_repeated_response_loss_review(
            repeated_response_loss_review
        ),
    )


def load_lambda_future_launch_hold(path: str | Path) -> LambdaFutureLaunchHoldReport:
    return LambdaFutureLaunchHoldReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_future_launch_hold(
    path: str | Path,
    report: LambdaFutureLaunchHoldReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
