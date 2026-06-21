"""M034C incident closeout evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m034_incident_report import (
    LambdaM034IncidentReport,
    load_lambda_m034_incident_report,
)


class LambdaM034IncidentCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_status: str
    closeout_succeeded: bool
    incident_future_launch_blocked: bool
    future_launch_hold_active: bool = True
    crash_safe_diagnostics_required: bool = True
    manual_review_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034IncidentCloseoutReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 closeout cannot enable launch")
        if not self.future_launch_hold_active:
            raise ValueError("M034D closeout cannot release crash-safe diagnostics hold")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def closeout_m034_incident(
    incident: LambdaM034IncidentReport,
) -> LambdaM034IncidentCloseoutReport:
    closed = incident.incident_status.startswith("closed_")
    blockers: list[str] = []
    if not closed:
        blockers.append("m034_incident_not_closed")
    if incident.console_confirmation.confirmation_status == "not_provided":
        blockers.append("manual_console_confirmation_missing")
    blockers.append("crash_safe_diagnostics_hardening_required")
    if not incident.transport_error_persisted:
        blockers.append("m034c_transport_error_not_persisted")
    return LambdaM034IncidentCloseoutReport(
        incident_status=incident.incident_status,
        closeout_succeeded=closed,
        incident_future_launch_blocked=not closed,
        future_launch_hold_active=True,
        crash_safe_diagnostics_required=True,
        manual_review_required=not closed,
        blockers=blockers,
        warnings=[
            *incident.warnings,
            "future launch remains held until crash-safe diagnostics hardening passes",
        ],
    )


def closeout_m034_incident_from_path(path: str | Path) -> LambdaM034IncidentCloseoutReport:
    return closeout_m034_incident(load_lambda_m034_incident_report(path))


def write_lambda_m034_incident_closeout(
    path: str | Path,
    report: LambdaM034IncidentCloseoutReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
