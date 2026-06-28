"""Aggregate M082 DiLoCo-shaped synthetic closeout and optimizer planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    load_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    load_lambda_diloco_optimizer_policy,
)
from decodilo.lambda_cloud.diloco_optimizer_readiness import (
    load_lambda_diloco_optimizer_readiness,
)
from decodilo.lambda_cloud.diloco_synthetic_artifact_audit import (
    load_lambda_diloco_synthetic_artifact_audit,
)
from decodilo.lambda_cloud.diloco_synthetic_closeout import (
    load_lambda_diloco_synthetic_closeout,
)
from decodilo.lambda_cloud.diloco_synthetic_reconciliation import (
    load_lambda_diloco_synthetic_reconciliation,
)
from decodilo.lambda_cloud.diloco_synthetic_success_record import (
    load_lambda_diloco_synthetic_success_record,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    load_lambda_m083r_diloco_optimizer_authorization,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_runbook_preview import (
    load_lambda_m083r_diloco_optimizer_runbook_preview,
)


class LambdaM082Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082"
    report_passed: bool
    diloco_synthetic_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    artifact_audit_passed: bool
    artifact_sha256: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    optimizer_readiness_status: str
    optimizer_discovery_status: str
    selected_optimizer_command_argv: list[str] = Field(default_factory=list)
    optimizer_policy_status: str
    m083r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m083r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM082Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M082 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M082 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m082_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    optimizer_readiness: str | Path,
    optimizer_discovery: str | Path,
    optimizer_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM082Report:
    record = load_lambda_diloco_synthetic_success_record(success_record)
    reconcile = load_lambda_diloco_synthetic_reconciliation(reconciliation)
    close = load_lambda_diloco_synthetic_closeout(closeout)
    audit = load_lambda_diloco_synthetic_artifact_audit(artifact_audit)
    ready = load_lambda_diloco_optimizer_readiness(optimizer_readiness)
    discovery = load_lambda_diloco_optimizer_command_discovery(optimizer_discovery)
    policy = load_lambda_diloco_optimizer_policy(optimizer_policy)
    auth = load_lambda_m083r_diloco_optimizer_authorization(authorization)
    preview = load_lambda_m083r_diloco_optimizer_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.success_status != "remote_diloco_shaped_synthetic_success":
        blockers.append("m081r2_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m081r2_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m081r2_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("diloco_artifact_audit_not_passed")
    if ready.readiness_status != "ready_for_future_diloco_optimizer_planning":
        blockers.append("diloco_optimizer_readiness_not_ready")

    m083r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_optimizer_command":
        m083r_blockers.append("no_safe_diloco_optimizer_command_found")
    if policy.policy_status != "policy_passed":
        m083r_blockers.append("diloco_optimizer_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m083r_diloco_optimizer_smoke":
        m083r_blockers.append("m083r_not_authorized")
    return LambdaM082Report(
        report_passed=not blockers,
        diloco_synthetic_success_status=record.success_status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        artifact_audit_passed=audit.artifact_audit_passed,
        artifact_sha256=audit.artifact_sha256,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        optimizer_readiness_status=ready.readiness_status,
        optimizer_discovery_status=discovery.discovery_status,
        selected_optimizer_command_argv=discovery.argv_tokens,
        optimizer_policy_status=policy.policy_status,
        m083r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m083r_blockers=m083r_blockers,
        blockers=blockers,
        warnings=[
            "M082 is offline; M083R requires a separate future supervised confirmation",
            "M083R remains blocked unless a safe optimizer-fidelity command exists",
        ],
    )


def load_lambda_m082_report(path: str | Path) -> LambdaM082Report:
    return LambdaM082Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m082_report(path: str | Path, report: LambdaM082Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
