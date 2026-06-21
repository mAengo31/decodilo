"""Future launch hold after M034C transport-error incident."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.crash_safe_transport_diagnostics import (
    LambdaCrashSafeTransportDiagnosticsReport,
    load_lambda_crash_safe_transport_diagnostics,
)
from decodilo.lambda_cloud.m034_incident_report import (
    LambdaM034IncidentReport,
    load_lambda_m034_incident_report,
)


class LambdaM034FutureLaunchHoldReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    future_launch_hold_active: bool
    hold_reasons: list[str] = Field(default_factory=list)
    required_clearance_items: list[str] = Field(default_factory=list)
    incident_closeout_required: bool
    crash_safe_diagnostics_required: bool
    repeated_response_loss_review_required: bool = True
    operator_reapproval_required: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034FutureLaunchHoldReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 future launch hold cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034_future_launch_hold(
    *,
    incident_report: LambdaM034IncidentReport,
    crash_safe_diagnostics: LambdaCrashSafeTransportDiagnosticsReport | None = None,
) -> LambdaM034FutureLaunchHoldReport:
    incident_open = not incident_report.incident_status.startswith("closed_")
    diagnostics_missing = (
        crash_safe_diagnostics is None
        or not crash_safe_diagnostics.diagnostics_hardening_accepted
    )
    hold_reasons: list[str] = []
    required: list[str] = []
    if incident_open:
        hold_reasons.append("m034_incident_open")
        required.append("close M034C incident")
    if diagnostics_missing:
        hold_reasons.append("crash_safe_diagnostics_not_accepted")
        required.append("prove crash-safe transport diagnostics")
    required.append("obtain fresh operator approval for any future launch")
    return LambdaM034FutureLaunchHoldReport(
        future_launch_hold_active=bool(incident_open or diagnostics_missing),
        hold_reasons=hold_reasons,
        required_clearance_items=required,
        incident_closeout_required=incident_open,
        crash_safe_diagnostics_required=diagnostics_missing,
    )


def build_lambda_m034_future_launch_hold_from_paths(
    *,
    incident_report: str | Path,
    crash_safe_diagnostics: str | Path | None = None,
) -> LambdaM034FutureLaunchHoldReport:
    diagnostics = None
    if crash_safe_diagnostics is not None and Path(crash_safe_diagnostics).exists():
        diagnostics = load_lambda_crash_safe_transport_diagnostics(crash_safe_diagnostics)
    return build_lambda_m034_future_launch_hold(
        incident_report=load_lambda_m034_incident_report(incident_report),
        crash_safe_diagnostics=diagnostics,
    )


def load_lambda_m034_future_launch_hold(path: str | Path) -> LambdaM034FutureLaunchHoldReport:
    return LambdaM034FutureLaunchHoldReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_future_launch_hold(
    path: str | Path,
    report: LambdaM034FutureLaunchHoldReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
