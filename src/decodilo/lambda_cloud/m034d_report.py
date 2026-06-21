"""Combined M034D incident closeout and hardening report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.crash_safe_transport_diagnostics import (
    LambdaCrashSafeTransportDiagnosticsReport,
    load_lambda_crash_safe_transport_diagnostics,
)
from decodilo.lambda_cloud.launch_failure_journal_recovery import (
    LambdaLaunchFailureJournalRecoveryReport,
    load_lambda_launch_failure_journal_recovery,
)
from decodilo.lambda_cloud.m034_future_launch_hold import (
    LambdaM034FutureLaunchHoldReport,
    load_lambda_m034_future_launch_hold,
)
from decodilo.lambda_cloud.m034_incident_closeout import (
    LambdaM034IncidentCloseoutReport,
)
from decodilo.lambda_cloud.m034_incident_report import (
    LambdaM034IncidentReport,
    load_lambda_m034_incident_report,
)


class LambdaM034DReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_report: LambdaM034IncidentReport
    closeout: LambdaM034IncidentCloseoutReport | None = None
    journal_recovery: LambdaLaunchFailureJournalRecoveryReport | None = None
    crash_safe_diagnostics: LambdaCrashSafeTransportDiagnosticsReport | None = None
    future_launch_hold: LambdaM034FutureLaunchHoldReport
    diagnostics_hardening_accepted: bool
    closeout_succeeded: bool
    future_launch_hold_active: bool
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034DReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034D report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034d_report(
    *,
    incident_report: LambdaM034IncidentReport,
    future_launch_hold: LambdaM034FutureLaunchHoldReport,
    closeout: LambdaM034IncidentCloseoutReport | None = None,
    journal_recovery: LambdaLaunchFailureJournalRecoveryReport | None = None,
    crash_safe_diagnostics: LambdaCrashSafeTransportDiagnosticsReport | None = None,
) -> LambdaM034DReport:
    accepted = bool(
        crash_safe_diagnostics
        and crash_safe_diagnostics.diagnostics_hardening_accepted
    )
    closed = bool(closeout and closeout.closeout_succeeded)
    return LambdaM034DReport(
        incident_report=incident_report,
        closeout=closeout,
        journal_recovery=journal_recovery,
        crash_safe_diagnostics=crash_safe_diagnostics,
        future_launch_hold=future_launch_hold,
        diagnostics_hardening_accepted=accepted,
        closeout_succeeded=closed,
        future_launch_hold_active=future_launch_hold.future_launch_hold_active,
        warnings=[
            "M034D is closeout/hardening only; it does not launch or terminate",
            *incident_report.warnings,
            *future_launch_hold.hold_reasons,
        ],
    )


def build_lambda_m034d_report_from_paths(
    *,
    incident_report: str | Path,
    future_launch_hold: str | Path,
    closeout: str | Path | None = None,
    journal_recovery: str | Path | None = None,
    crash_safe_diagnostics: str | Path | None = None,
) -> LambdaM034DReport:
    closeout_obj = None
    if closeout is not None and Path(closeout).exists():
        from decodilo.lambda_cloud.m034_incident_closeout import (
            LambdaM034IncidentCloseoutReport,
        )

        closeout_obj = LambdaM034IncidentCloseoutReport.model_validate_json(
            Path(closeout).read_text(encoding="utf-8")
        )
    recovery_obj = (
        load_lambda_launch_failure_journal_recovery(journal_recovery)
        if journal_recovery is not None and Path(journal_recovery).exists()
        else None
    )
    diagnostics_obj = (
        load_lambda_crash_safe_transport_diagnostics(crash_safe_diagnostics)
        if crash_safe_diagnostics is not None and Path(crash_safe_diagnostics).exists()
        else None
    )
    return build_lambda_m034d_report(
        incident_report=load_lambda_m034_incident_report(incident_report),
        closeout=closeout_obj,
        journal_recovery=recovery_obj,
        crash_safe_diagnostics=diagnostics_obj,
        future_launch_hold=load_lambda_m034_future_launch_hold(future_launch_hold),
    )


def write_lambda_m034d_report(path: str | Path, report: LambdaM034DReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
