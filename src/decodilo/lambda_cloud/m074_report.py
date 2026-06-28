"""Aggregate M074 tiny-smoke closeout and future runtime/protocol smoke report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    load_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_runbook_preview import (
    load_lambda_m075r_runtime_protocol_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    load_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    load_lambda_runtime_protocol_smoke_policy,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    load_lambda_runtime_protocol_smoke_readiness,
)
from decodilo.lambda_cloud.tiny_smoke_artifact_audit import (
    load_lambda_tiny_smoke_artifact_audit,
)
from decodilo.lambda_cloud.tiny_smoke_closeout import load_lambda_tiny_smoke_closeout
from decodilo.lambda_cloud.tiny_smoke_reconciliation import (
    load_lambda_tiny_smoke_reconciliation,
)
from decodilo.lambda_cloud.tiny_smoke_success_record import (
    load_lambda_tiny_smoke_success_record,
)


class LambdaM074Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074"
    report_passed: bool
    tiny_smoke_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    artifact_audit_passed: bool
    runtime_protocol_readiness_status: str
    runtime_protocol_discovery_status: str
    selected_runtime_protocol_command_argv: list[str] = Field(default_factory=list)
    runtime_protocol_policy_status: str
    m075r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m075r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM074Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M074 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M074 report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m074_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    runtime_readiness: str | Path,
    runtime_discovery: str | Path,
    runtime_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM074Report:
    record = load_lambda_tiny_smoke_success_record(success_record)
    reconcile = load_lambda_tiny_smoke_reconciliation(reconciliation)
    close = load_lambda_tiny_smoke_closeout(closeout)
    audit = load_lambda_tiny_smoke_artifact_audit(artifact_audit)
    readiness = load_lambda_runtime_protocol_smoke_readiness(runtime_readiness)
    discovery = load_lambda_runtime_protocol_smoke_discovery(runtime_discovery)
    policy = load_lambda_runtime_protocol_smoke_policy(runtime_policy)
    auth = load_lambda_m075r_runtime_protocol_smoke_authorization(authorization)
    preview = load_lambda_m075r_runtime_protocol_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.status != "tiny_smoke_success":
        blockers.append("m073r2_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m073r2_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m073r2_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("tiny_smoke_artifact_audit_not_passed")
    if readiness.readiness_status != "ready_for_future_runtime_protocol_smoke_planning":
        blockers.append("runtime_protocol_smoke_readiness_not_ready")

    m075r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_runtime_protocol_smoke_command":
        m075r_blockers.append("no_safe_runtime_protocol_smoke_command_found")
    if policy.policy_status != "policy_passed":
        m075r_blockers.append("runtime_protocol_smoke_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m075r_runtime_protocol_smoke":
        m075r_blockers.append("m075r_not_authorized")
    return LambdaM074Report(
        report_passed=not blockers,
        tiny_smoke_success_status=record.status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        artifact_audit_passed=audit.artifact_audit_passed,
        runtime_protocol_readiness_status=readiness.readiness_status,
        runtime_protocol_discovery_status=discovery.discovery_status,
        selected_runtime_protocol_command_argv=discovery.argv_tokens,
        runtime_protocol_policy_status=policy.policy_status,
        m075r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m075r_blockers=m075r_blockers,
        blockers=blockers,
        warnings=[
            "M074 is offline; M075R requires a separate future supervised confirmation",
        ],
    )


def load_lambda_m074_report(path: str | Path) -> LambdaM074Report:
    return LambdaM074Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m074_report(path: str | Path, report: LambdaM074Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
