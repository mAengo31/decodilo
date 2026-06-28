"""Aggregate M080 learner/syncer smoke closeout and DiLoCo planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    load_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    load_lambda_diloco_synthetic_policy,
)
from decodilo.lambda_cloud.diloco_synthetic_readiness import (
    load_lambda_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.learner_syncer_smoke_artifact_audit import (
    load_lambda_learner_syncer_smoke_artifact_audit,
)
from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    load_lambda_learner_syncer_smoke_closeout,
)
from decodilo.lambda_cloud.learner_syncer_smoke_reconciliation import (
    load_lambda_learner_syncer_smoke_reconciliation,
)
from decodilo.lambda_cloud.learner_syncer_smoke_success_record import (
    load_lambda_learner_syncer_smoke_success_record,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    load_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_runbook_preview import (
    load_lambda_m081r_diloco_synthetic_runbook_preview,
)


class LambdaM080Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    report_passed: bool
    learner_syncer_smoke_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    artifact_audit_passed: bool
    diloco_synthetic_readiness_status: str
    diloco_synthetic_discovery_status: str
    selected_diloco_synthetic_command_argv: list[str] = Field(default_factory=list)
    diloco_synthetic_policy_status: str
    m081r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m081r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM080Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M080 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M080 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m080_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM080Report:
    record = load_lambda_learner_syncer_smoke_success_record(success_record)
    reconcile = load_lambda_learner_syncer_smoke_reconciliation(reconciliation)
    close = load_lambda_learner_syncer_smoke_closeout(closeout)
    audit = load_lambda_learner_syncer_smoke_artifact_audit(artifact_audit)
    ready = load_lambda_diloco_synthetic_readiness(readiness)
    discovery = load_lambda_diloco_synthetic_command_discovery(command_discovery)
    experiment_policy = load_lambda_diloco_synthetic_policy(policy)
    auth = load_lambda_m081r_diloco_synthetic_authorization(authorization)
    preview = load_lambda_m081r_diloco_synthetic_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.success_status != "remote_learner_syncer_smoke_success":
        blockers.append("m079r2_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m079r2_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m079r2_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("learner_syncer_artifact_audit_not_passed")
    if ready.readiness_status != "ready_for_future_diloco_synthetic_planning":
        blockers.append("diloco_synthetic_readiness_not_ready")

    m081r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_synthetic_command":
        m081r_blockers.append("no_safe_diloco_synthetic_command_found")
    if experiment_policy.policy_status != "policy_passed":
        m081r_blockers.append("diloco_synthetic_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m081r_diloco_synthetic_experiment":
        m081r_blockers.append("m081r_not_authorized")
    return LambdaM080Report(
        report_passed=not blockers,
        learner_syncer_smoke_success_status=record.success_status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        artifact_audit_passed=audit.artifact_audit_passed,
        diloco_synthetic_readiness_status=ready.readiness_status,
        diloco_synthetic_discovery_status=discovery.discovery_status,
        selected_diloco_synthetic_command_argv=discovery.argv_tokens,
        diloco_synthetic_policy_status=experiment_policy.policy_status,
        m081r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m081r_blockers=m081r_blockers,
        blockers=blockers,
        warnings=[
            "M080 is offline; M081R requires a separate future supervised confirmation",
        ],
    )


def load_lambda_m080_report(path: str | Path) -> LambdaM080Report:
    return LambdaM080Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m080_report(path: str | Path, report: LambdaM080Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
