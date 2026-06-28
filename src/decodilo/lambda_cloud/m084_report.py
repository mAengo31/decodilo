"""Aggregate M084 optimizer closeout and integrated DiLoCo planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_artifact_audit import (
    load_lambda_diloco_optimizer_artifact_audit,
)
from decodilo.lambda_cloud.diloco_optimizer_closeout import (
    load_lambda_diloco_optimizer_closeout,
)
from decodilo.lambda_cloud.diloco_optimizer_success_record import (
    load_lambda_diloco_optimizer_success_record,
)
from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    load_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    load_lambda_integrated_diloco_policy,
)
from decodilo.lambda_cloud.integrated_diloco_synthetic_readiness import (
    load_lambda_integrated_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    load_lambda_m085r_integrated_diloco_authorization,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_runbook_preview import (
    load_lambda_m085r_integrated_diloco_runbook_preview,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    load_lambda_ssh_proven_candidate_history_update,
)


class LambdaM084Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084"
    report_passed: bool
    optimizer_success_status: str
    optimizer_closeout_status: str
    optimizer_closeout_succeeded: bool
    optimizer_artifact_audit_passed: bool
    optimizer_artifact_sha256: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    max_abs_error: float | None = None
    ssh_history_update_status: str
    gpu_1x_a10_us_west_1_recorded: bool
    gpu_1x_a10_us_east_1_preserved: bool
    integrated_readiness_status: str
    integrated_discovery_status: str
    selected_integrated_command_argv: list[str] = Field(default_factory=list)
    integrated_policy_status: str
    m085r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m085r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM084Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M084 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M084 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m084_report_from_paths(
    *,
    optimizer_success_record: str | Path,
    optimizer_closeout: str | Path,
    optimizer_artifact_audit: str | Path,
    ssh_readiness_history: str | Path,
    integrated_readiness: str | Path,
    integrated_discovery: str | Path,
    integrated_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM084Report:
    record = load_lambda_diloco_optimizer_success_record(optimizer_success_record)
    closeout = load_lambda_diloco_optimizer_closeout(optimizer_closeout)
    audit = load_lambda_diloco_optimizer_artifact_audit(optimizer_artifact_audit)
    ssh_history = load_lambda_ssh_proven_candidate_history_update(ssh_readiness_history)
    readiness = load_lambda_integrated_diloco_synthetic_readiness(integrated_readiness)
    discovery = load_lambda_integrated_diloco_command_discovery(integrated_discovery)
    policy = load_lambda_integrated_diloco_policy(integrated_policy)
    auth = load_lambda_m085r_integrated_diloco_authorization(authorization)
    preview = load_lambda_m085r_integrated_diloco_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.success_status != "remote_diloco_optimizer_smoke_success":
        blockers.append("m083r_success_record_not_success")
    if not closeout.closeout_succeeded:
        blockers.append("m083r_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("optimizer_artifact_audit_not_passed")
    if ssh_history.update_status != "ssh_proven_candidate_history_updated":
        blockers.append("ssh_history_update_not_passed")
    if readiness.readiness_status != "ready_for_future_integrated_diloco_planning":
        blockers.append("integrated_diloco_readiness_not_ready")

    m085r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_integrated_diloco_command":
        m085r_blockers.append("no_safe_integrated_diloco_command_found")
    if policy.policy_status != "policy_passed":
        m085r_blockers.append("integrated_diloco_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m085r_integrated_diloco_smoke":
        m085r_blockers.append("m085r_not_authorized")
    return LambdaM084Report(
        report_passed=not blockers,
        optimizer_success_status=record.success_status,
        optimizer_closeout_status=closeout.closeout_status,
        optimizer_closeout_succeeded=closeout.closeout_succeeded,
        optimizer_artifact_audit_passed=audit.artifact_audit_passed,
        optimizer_artifact_sha256=audit.artifact_sha256,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        max_abs_error=record.max_abs_error,
        ssh_history_update_status=ssh_history.update_status,
        gpu_1x_a10_us_west_1_recorded=ssh_history.gpu_1x_a10_us_west_1_recorded,
        gpu_1x_a10_us_east_1_preserved=ssh_history.gpu_1x_a10_us_east_1_preserved,
        integrated_readiness_status=readiness.readiness_status,
        integrated_discovery_status=discovery.discovery_status,
        selected_integrated_command_argv=discovery.argv_tokens,
        integrated_policy_status=policy.policy_status,
        m085r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        m085r_blockers=m085r_blockers,
        blockers=blockers,
        warnings=[
            "M084 is offline; M085R requires a separate future supervised confirmation",
            "M085R remains blocked unless a safe integrated DiLoCo command exists",
        ],
    )


def load_lambda_m084_report(path: str | Path) -> LambdaM084Report:
    return LambdaM084Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m084_report(path: str | Path, report: LambdaM084Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
