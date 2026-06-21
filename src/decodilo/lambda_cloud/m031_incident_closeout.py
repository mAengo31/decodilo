"""M031 incident closeout evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m031_incident_report import (
    LambdaM031IncidentReport,
    load_lambda_m031_incident_report,
)


class LambdaM031IncidentCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_status: str
    closeout_succeeded: bool
    incident_future_launch_blocked: bool
    global_future_launch_blocked: bool = True
    repeated_response_loss_review_required: bool = True
    manual_review_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def closeout_m031_incident(
    incident: LambdaM031IncidentReport,
) -> LambdaM031IncidentCloseoutReport:
    closed = incident.incident_status.startswith("closed_")
    blockers: list[str] = []
    if not closed:
        blockers.append("m031_incident_not_closed")
    if incident.console_confirmation.confirmation_status == "not_provided":
        blockers.append("manual_console_confirmation_missing")
    if closed:
        blockers.append("repeated_response_loss_review_required")
    return LambdaM031IncidentCloseoutReport(
        incident_status=incident.incident_status,
        closeout_succeeded=closed,
        incident_future_launch_blocked=not closed,
        global_future_launch_blocked=True,
        repeated_response_loss_review_required=True,
        manual_review_required=not closed,
        blockers=blockers,
        warnings=[
            *incident.warnings,
            "future launch remains globally held until repeated response-loss review passes",
        ],
    )


def closeout_m031_incident_from_path(path: str | Path) -> LambdaM031IncidentCloseoutReport:
    return closeout_m031_incident(load_lambda_m031_incident_report(path))


def write_lambda_m031_incident_closeout(
    path: str | Path,
    report: LambdaM031IncidentCloseoutReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
