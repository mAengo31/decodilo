"""Aggregate M072 first-experiment closeout and future tiny-smoke report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_closeout import (
    load_lambda_first_experiment_closeout,
)
from decodilo.lambda_cloud.first_experiment_reconciliation import (
    load_lambda_first_experiment_reconciliation,
)
from decodilo.lambda_cloud.first_experiment_success_record import (
    load_lambda_first_experiment_success_record,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    load_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_runbook_preview import (
    load_lambda_m073r_tiny_smoke_runbook_preview,
)
from decodilo.lambda_cloud.remote_artifact_audit import load_lambda_remote_artifact_audit
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    load_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    load_lambda_tiny_decodilo_smoke_policy,
)


class LambdaM072Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072"
    report_passed: bool
    m071r_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    artifact_audit_passed: bool
    tiny_smoke_discovery_status: str
    selected_smoke_command_argv: list[str] = Field(default_factory=list)
    tiny_smoke_policy_status: str
    m073r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m073r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM072Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M072 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M072 report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m072_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    smoke_discovery: str | Path,
    smoke_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM072Report:
    record = load_lambda_first_experiment_success_record(success_record)
    reconcile = load_lambda_first_experiment_reconciliation(reconciliation)
    close = load_lambda_first_experiment_closeout(closeout)
    audit = load_lambda_remote_artifact_audit(artifact_audit)
    discovery = load_lambda_tiny_decodilo_smoke_discovery(smoke_discovery)
    policy = load_lambda_tiny_decodilo_smoke_policy(smoke_policy)
    auth = load_lambda_m073r_tiny_smoke_authorization(authorization)
    preview = load_lambda_m073r_tiny_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.status != "first_experiment_runtime_success":
        blockers.append("m071r_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m071r_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m071r_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("artifact_audit_not_passed")
    m073r_blockers: list[str] = []
    if discovery.discovery_status not in {
        "found_safe_tiny_smoke_command",
        "safe_tiny_smoke_command_found",
    }:
        m073r_blockers.append("no_safe_tiny_smoke_command_found")
    if policy.policy_status != "policy_passed":
        m073r_blockers.append("tiny_smoke_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m073r_tiny_decodilo_smoke":
        m073r_blockers.append("m073r_not_authorized")
    return LambdaM072Report(
        report_passed=not blockers,
        m071r_success_status=record.status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        artifact_audit_passed=audit.artifact_audit_passed,
        tiny_smoke_discovery_status=discovery.discovery_status,
        selected_smoke_command_argv=discovery.argv_tokens,
        tiny_smoke_policy_status=policy.policy_status,
        m073r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m073r_blockers=m073r_blockers,
        blockers=blockers,
        warnings=[
            "M072 is offline; M073R requires a separate future supervised confirmation",
        ],
    )


def load_lambda_m072_report(path: str | Path) -> LambdaM072Report:
    return LambdaM072Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m072_report(path: str | Path, report: LambdaM072Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
