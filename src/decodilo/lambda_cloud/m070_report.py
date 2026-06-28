"""Aggregate M070 closeout and future first-experiment report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    load_lambda_first_experiment_command_discovery,
)
from decodilo.lambda_cloud.first_experiment_readiness import (
    load_lambda_first_experiment_readiness,
)
from decodilo.lambda_cloud.m071r_first_experiment_authorization import (
    load_lambda_m071r_first_experiment_authorization,
)
from decodilo.lambda_cloud.m071r_first_experiment_runbook_preview import (
    load_lambda_m071r_first_experiment_runbook_preview,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_closeout import (
    load_lambda_remote_decodilo_vslice_closeout,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_reconciliation import (
    load_lambda_remote_decodilo_vslice_reconciliation,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    load_lambda_remote_decodilo_vslice_success_record,
)


class LambdaM070Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M070"
    report_passed: bool
    m069r_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    first_experiment_readiness_status: str
    command_discovery_status: str
    discovered_command_argv: list[str] = Field(default_factory=list)
    m071r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM070Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M070 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M070 report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m070_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    readiness: str | Path,
    command_discovery: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM070Report:
    record = load_lambda_remote_decodilo_vslice_success_record(success_record)
    reconcile = load_lambda_remote_decodilo_vslice_reconciliation(reconciliation)
    close = load_lambda_remote_decodilo_vslice_closeout(closeout)
    ready = load_lambda_first_experiment_readiness(readiness)
    discovery = load_lambda_first_experiment_command_discovery(command_discovery)
    auth = load_lambda_m071r_first_experiment_authorization(authorization)
    preview = load_lambda_m071r_first_experiment_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.status != "remote_decodilo_vslice_success":
        blockers.append("m069r_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m069r_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m069r_closeout_not_succeeded")
    if ready.readiness_status != "ready_for_future_first_experiment_planning":
        blockers.append("first_experiment_not_ready")
    if discovery.discovery_status != "safe_experiment_command_found":
        blockers.append("no_safe_experiment_command_found")
    if auth.authorization_status != "authorized_for_future_m071r_first_experiment_attempt":
        blockers.append("m071r_not_authorized")
    return LambdaM070Report(
        report_passed=not blockers,
        m069r_success_status=record.status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        first_experiment_readiness_status=ready.readiness_status,
        command_discovery_status=discovery.discovery_status,
        discovered_command_argv=discovery.argv_tokens,
        m071r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        blockers=blockers,
        warnings=[
            "M070 is offline; M071R requires a separate fresh supervised confirmation",
        ],
    )


def load_lambda_m070_report(path: str | Path) -> LambdaM070Report:
    return LambdaM070Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m070_report(path: str | Path, report: LambdaM070Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
