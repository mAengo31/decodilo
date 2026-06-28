"""Aggregate M088 parameter-fragment closeout and bounded-experiment planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    load_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    load_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    load_lambda_bounded_diloco_experiment_readiness,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    load_lambda_m089r_bounded_diloco_experiment_authorization,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_runbook_preview import (
    load_lambda_m089r_bounded_diloco_experiment_runbook_preview,
)
from decodilo.lambda_cloud.parameter_fragment_artifact_audit import (
    load_lambda_parameter_fragment_artifact_audit,
)
from decodilo.lambda_cloud.parameter_fragment_closeout import (
    load_lambda_parameter_fragment_closeout,
)
from decodilo.lambda_cloud.parameter_fragment_success_record import (
    load_lambda_parameter_fragment_success_record,
)
from decodilo.lambda_cloud.scaffold_complete_decision import (
    load_lambda_scaffold_complete_decision,
)
from decodilo.lambda_cloud.ssh_proven_candidate_history_update import (
    load_lambda_ssh_proven_candidate_history_update,
)


class LambdaM088Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    report_passed: bool
    parameter_fragment_success_status: str
    parameter_fragment_closeout_status: str
    parameter_fragment_closeout_succeeded: bool
    parameter_fragment_artifact_audit_passed: bool
    parameter_fragment_artifact_sha256: str | None = None
    parameter_fragment_semantics: str | None = None
    fragment_count: int | None = None
    max_abs_error: float | None = None
    overlap_semantics: str | None = None
    quantization_semantics: str | None = None
    ssh_history_update_status: str
    gpu_1x_a10_us_west_1_recorded: bool
    gpu_1x_a10_us_east_1_preserved: bool
    scaffold_status: str
    bounded_readiness_status: str
    bounded_discovery_status: str
    selected_bounded_command_argv: list[str] = Field(default_factory=list)
    bounded_policy_status: str
    m089r_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    m089r_blockers: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM088Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M088 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M088 report cannot carry closeout blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m088_report_from_paths(
    *,
    parameter_fragment_success_record: str | Path,
    parameter_fragment_closeout: str | Path,
    parameter_fragment_artifact_audit: str | Path,
    ssh_readiness_history: str | Path,
    scaffold_decision: str | Path,
    bounded_readiness: str | Path,
    bounded_discovery: str | Path,
    bounded_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM088Report:
    record = load_lambda_parameter_fragment_success_record(
        parameter_fragment_success_record
    )
    closeout = load_lambda_parameter_fragment_closeout(parameter_fragment_closeout)
    audit = load_lambda_parameter_fragment_artifact_audit(
        parameter_fragment_artifact_audit
    )
    ssh_history = load_lambda_ssh_proven_candidate_history_update(
        ssh_readiness_history
    )
    scaffold = load_lambda_scaffold_complete_decision(scaffold_decision)
    readiness = load_lambda_bounded_diloco_experiment_readiness(bounded_readiness)
    discovery = load_lambda_bounded_diloco_experiment_command_discovery(
        bounded_discovery
    )
    policy = load_lambda_bounded_diloco_experiment_policy(bounded_policy)
    auth = load_lambda_m089r_bounded_diloco_experiment_authorization(authorization)
    preview = load_lambda_m089r_bounded_diloco_experiment_runbook_preview(
        runbook_preview
    )
    blockers: list[str] = []
    if record.success_status != "remote_parameter_fragment_smoke_success":
        blockers.append("m087r_success_record_not_success")
    if not closeout.closeout_succeeded:
        blockers.append("m087r_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("parameter_fragment_artifact_audit_not_passed")
    if ssh_history.update_status != "ssh_proven_candidate_history_updated":
        blockers.append("ssh_history_update_not_passed")
    if scaffold.scaffold_status != "scaffold_validation_complete":
        blockers.append("scaffold_not_complete")
    if (
        readiness.readiness_status
        != "ready_for_first_bounded_synthetic_diloco_experiment_planning"
    ):
        blockers.append("bounded_experiment_readiness_not_ready")

    m089r_blockers: list[str] = []
    if discovery.discovery_status != "found_safe_bounded_diloco_experiment_command":
        m089r_blockers.append("no_safe_bounded_diloco_experiment_command_found")
    if policy.policy_status != "policy_passed":
        m089r_blockers.append("bounded_diloco_experiment_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m089r_bounded_diloco_experiment":
        m089r_blockers.append("m089r_not_authorized")
    return LambdaM088Report(
        report_passed=not blockers,
        parameter_fragment_success_status=record.success_status,
        parameter_fragment_closeout_status=closeout.closeout_status,
        parameter_fragment_closeout_succeeded=closeout.closeout_succeeded,
        parameter_fragment_artifact_audit_passed=audit.artifact_audit_passed,
        parameter_fragment_artifact_sha256=audit.artifact_sha256,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        fragment_count=record.fragment_count,
        max_abs_error=record.max_abs_error,
        overlap_semantics=record.overlap_semantics,
        quantization_semantics=record.quantization_semantics,
        ssh_history_update_status=ssh_history.update_status,
        gpu_1x_a10_us_west_1_recorded=ssh_history.gpu_1x_a10_us_west_1_recorded,
        gpu_1x_a10_us_east_1_preserved=ssh_history.gpu_1x_a10_us_east_1_preserved,
        scaffold_status=scaffold.scaffold_status,
        bounded_readiness_status=readiness.readiness_status,
        bounded_discovery_status=discovery.discovery_status,
        selected_bounded_command_argv=discovery.argv_tokens,
        bounded_policy_status=policy.policy_status,
        m089r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=(
            record.historical_billable_action_performed
        ),
        m089r_blockers=m089r_blockers,
        blockers=blockers,
        warnings=[
            "M088 is offline; M089R requires a separate future supervised confirmation",
            "M089R remains blocked unless a complete bounded synthetic DiLoCo "
            "experiment command exists",
        ],
    )


def load_lambda_m088_report(path: str | Path) -> LambdaM088Report:
    return LambdaM088Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m088_report(path: str | Path, report: LambdaM088Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
