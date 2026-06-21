"""M029 incident closeout evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    load_lambda_m029_incident_report,
)


class LambdaM029IncidentCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_status: str
    closeout_succeeded: bool
    second_launch_blocked: bool
    manual_review_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def closeout_m029_incident(
    incident: LambdaM029IncidentReport,
) -> LambdaM029IncidentCloseoutReport:
    closed = incident.incident_status.startswith("closed_")
    blockers: list[str] = []
    if not closed:
        blockers.append("m029_incident_not_closed")
    if incident.console_confirmation.confirmation_status == "not_provided":
        blockers.append("manual_console_confirmation_missing")
    return LambdaM029IncidentCloseoutReport(
        incident_status=incident.incident_status,
        closeout_succeeded=closed,
        second_launch_blocked=not closed,
        manual_review_required=not closed,
        blockers=blockers,
        warnings=incident.warnings,
    )


def closeout_m029_incident_from_path(path: str | Path) -> LambdaM029IncidentCloseoutReport:
    return closeout_m029_incident(load_lambda_m029_incident_report(path))


def write_lambda_m029_incident_closeout(
    path: str | Path,
    report: LambdaM029IncidentCloseoutReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
