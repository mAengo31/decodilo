"""Aggregate M078 synthetic experiment closeout and next experiment planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    load_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_runbook_preview import (
    load_lambda_m079r_next_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    load_lambda_next_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.next_synthetic_experiment_policy import (
    load_lambda_next_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.next_synthetic_experiment_readiness import (
    load_lambda_next_synthetic_experiment_readiness,
)
from decodilo.lambda_cloud.synthetic_experiment_artifact_audit import (
    load_lambda_synthetic_experiment_artifact_audit,
)
from decodilo.lambda_cloud.synthetic_experiment_closeout import (
    load_lambda_synthetic_experiment_closeout,
)
from decodilo.lambda_cloud.synthetic_experiment_reconciliation import (
    load_lambda_synthetic_experiment_reconciliation,
)
from decodilo.lambda_cloud.synthetic_experiment_success_record import (
    load_lambda_synthetic_experiment_success_record,
)


class LambdaM078Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M078"
    report_passed: bool
    synthetic_experiment_success_status: str
    reconciliation_passed: bool
    closeout_status: str
    closeout_succeeded: bool
    artifact_audit_passed: bool
    next_synthetic_experiment_readiness_status: str
    next_synthetic_experiment_discovery_status: str
    selected_next_synthetic_experiment_command_argv: list[str] = Field(
        default_factory=list
    )
    next_synthetic_experiment_policy_status: str
    m079r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m079r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM078Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M078 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M078 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m078_report_from_paths(
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
) -> LambdaM078Report:
    record = load_lambda_synthetic_experiment_success_record(success_record)
    reconcile = load_lambda_synthetic_experiment_reconciliation(reconciliation)
    close = load_lambda_synthetic_experiment_closeout(closeout)
    audit = load_lambda_synthetic_experiment_artifact_audit(artifact_audit)
    ready = load_lambda_next_synthetic_experiment_readiness(readiness)
    discovery = load_lambda_next_synthetic_experiment_discovery(command_discovery)
    experiment_policy = load_lambda_next_synthetic_experiment_policy(policy)
    auth = load_lambda_m079r_next_synthetic_experiment_authorization(authorization)
    preview = load_lambda_m079r_next_synthetic_experiment_runbook_preview(
        runbook_preview
    )
    blockers: list[str] = []
    if record.success_status != "first_remote_synthetic_experiment_success":
        blockers.append("m077r_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("m077r_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("m077r_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("synthetic_experiment_artifact_audit_not_passed")
    if (
        ready.readiness_status
        != "ready_for_future_next_synthetic_experiment_planning"
    ):
        blockers.append("next_synthetic_experiment_readiness_not_ready")

    m079r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_next_synthetic_experiment_command":
        m079r_blockers.append("no_safe_next_synthetic_experiment_command_found")
    if experiment_policy.policy_status != "policy_passed":
        m079r_blockers.append("next_synthetic_experiment_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m079r_next_synthetic_experiment":
        m079r_blockers.append("m079r_not_authorized")
    return LambdaM078Report(
        report_passed=not blockers,
        synthetic_experiment_success_status=record.success_status,
        reconciliation_passed=reconcile.reconciliation_passed,
        closeout_status=close.closeout_status,
        closeout_succeeded=close.closeout_succeeded,
        artifact_audit_passed=audit.artifact_audit_passed,
        next_synthetic_experiment_readiness_status=ready.readiness_status,
        next_synthetic_experiment_discovery_status=discovery.discovery_status,
        selected_next_synthetic_experiment_command_argv=discovery.argv_tokens,
        next_synthetic_experiment_policy_status=experiment_policy.policy_status,
        m079r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m079r_blockers=m079r_blockers,
        blockers=blockers,
        warnings=[
            "M078 is offline; M079R requires a separate future supervised confirmation",
        ],
    )


def load_lambda_m078_report(path: str | Path) -> LambdaM078Report:
    return LambdaM078Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m078_report(path: str | Path, report: LambdaM078Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
