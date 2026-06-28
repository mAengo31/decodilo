"""Aggregate M086 integrated closeout and parameter-fragment planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_artifact_audit import (
    load_lambda_integrated_diloco_artifact_audit,
)
from decodilo.lambda_cloud.integrated_diloco_closeout import (
    load_lambda_integrated_diloco_closeout,
)
from decodilo.lambda_cloud.integrated_diloco_success_record import (
    load_lambda_integrated_diloco_success_record,
)
from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    load_lambda_m087r_parameter_fragment_authorization,
)
from decodilo.lambda_cloud.m087r_parameter_fragment_runbook_preview import (
    load_lambda_m087r_parameter_fragment_runbook_preview,
)
from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    load_lambda_parameter_fragment_command_discovery,
)
from decodilo.lambda_cloud.parameter_fragment_policy import (
    load_lambda_parameter_fragment_policy,
)
from decodilo.lambda_cloud.parameter_fragment_readiness import (
    load_lambda_parameter_fragment_readiness,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    load_lambda_ssh_proven_candidate_history_update,
)


class LambdaM086Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086"
    report_passed: bool
    integrated_success_status: str
    integrated_closeout_status: str
    integrated_closeout_succeeded: bool
    integrated_artifact_audit_passed: bool
    integrated_artifact_sha256: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    protocol_optimizer_link_check_passed: bool | None = None
    max_abs_error: float | None = None
    ssh_history_update_status: str
    gpu_1x_a10_us_west_1_recorded: bool
    gpu_1x_a10_us_east_1_preserved: bool
    parameter_fragment_readiness_status: str
    parameter_fragment_discovery_status: str
    selected_parameter_fragment_command_argv: list[str] = Field(default_factory=list)
    parameter_fragment_policy_status: str
    m087r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m087r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM086Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M086 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M086 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m086_report_from_paths(
    *,
    success_record: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    ssh_readiness_history: str | Path,
    fragment_readiness: str | Path,
    fragment_discovery: str | Path,
    fragment_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM086Report:
    record = load_lambda_integrated_diloco_success_record(success_record)
    closeout_report = load_lambda_integrated_diloco_closeout(closeout)
    audit = load_lambda_integrated_diloco_artifact_audit(artifact_audit)
    ssh_history = load_lambda_ssh_proven_candidate_history_update(
        ssh_readiness_history
    )
    readiness = load_lambda_parameter_fragment_readiness(fragment_readiness)
    discovery = load_lambda_parameter_fragment_command_discovery(fragment_discovery)
    policy = load_lambda_parameter_fragment_policy(fragment_policy)
    auth = load_lambda_m087r_parameter_fragment_authorization(authorization)
    preview = load_lambda_m087r_parameter_fragment_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.success_status != "remote_integrated_diloco_synthetic_success":
        blockers.append("m085r_success_record_not_success")
    if not closeout_report.closeout_succeeded:
        blockers.append("m085r_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("integrated_artifact_audit_not_passed")
    if ssh_history.update_status != "ssh_proven_candidate_history_updated":
        blockers.append("ssh_history_update_not_passed")
    if readiness.readiness_status != "ready_for_future_parameter_fragment_planning":
        blockers.append("parameter_fragment_readiness_not_ready")

    m087r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_parameter_fragment_command":
        m087r_blockers.append("no_safe_parameter_fragment_command_found")
    if policy.policy_status != "policy_passed":
        m087r_blockers.append("parameter_fragment_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m087r_parameter_fragment_smoke":
        m087r_blockers.append("m087r_not_authorized")
    return LambdaM086Report(
        report_passed=not blockers,
        integrated_success_status=record.success_status,
        integrated_closeout_status=closeout_report.closeout_status,
        integrated_closeout_succeeded=closeout_report.closeout_succeeded,
        integrated_artifact_audit_passed=audit.artifact_audit_passed,
        integrated_artifact_sha256=audit.artifact_sha256,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        protocol_optimizer_link_check_passed=(
            record.protocol_optimizer_link_check_passed
        ),
        max_abs_error=record.max_abs_error,
        ssh_history_update_status=ssh_history.update_status,
        gpu_1x_a10_us_west_1_recorded=ssh_history.gpu_1x_a10_us_west_1_recorded,
        gpu_1x_a10_us_east_1_preserved=ssh_history.gpu_1x_a10_us_east_1_preserved,
        parameter_fragment_readiness_status=readiness.readiness_status,
        parameter_fragment_discovery_status=discovery.discovery_status,
        selected_parameter_fragment_command_argv=discovery.argv_tokens,
        parameter_fragment_policy_status=policy.policy_status,
        m087r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=(
            record.historical_billable_action_performed
        ),
        m087r_blockers=m087r_blockers,
        blockers=blockers,
        warnings=[
            "M086 is offline; M087R requires a separate future supervised confirmation",
            "M087R remains blocked unless a safe parameter-fragment command exists",
        ],
    )


def load_lambda_m086_report(path: str | Path) -> LambdaM086Report:
    return LambdaM086Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m086_report(path: str | Path, report: LambdaM086Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
