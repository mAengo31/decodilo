"""Success record for the completed M051B metadata-only Lambda bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport

LambdaMetadataBootstrapSuccessStatus = Literal[
    "metadata_bootstrap_success",
    "metadata_bootstrap_partial",
    "metadata_bootstrap_failed",
]


class LambdaMetadataBootstrapSuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_schema_version: int = 1
    milestone: str = "M051B"
    run_id: str
    source_workdir: str
    post_discovery_path: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    bootstrap_mode: str = "metadata_only"
    launch_request_sent: bool
    launch_response_received: bool
    launch_status_code: int | None = None
    launch_content_type: str | None = None
    launch_body_size: int | None = None
    launch_response_classification: str | None = None
    owned_instance_id_redacted: str | None = None
    readonly_verify_running_result: str | None = None
    metadata_collected: dict[str, Any] = Field(default_factory=dict)
    ssh_attempted: bool
    remote_command_attempted: bool
    package_install_attempted: bool
    training_attempted: bool
    termination_request_sent: bool
    termination_response_received: bool
    termination_status_code: int | None = None
    termination_content_type: str | None = None
    termination_body_size: int | None = None
    readonly_verify_terminated_result: str | None = None
    termination_verified: bool
    manual_review_required: bool
    mutating_operations: int
    historical_billable_action_performed: bool
    elapsed_seconds: float
    estimated_spend: float
    conservative_estimated_spend: float | None = None
    final_instance_count: int
    final_unmanaged_count: int
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    secret_scan_passed: bool
    status: LambdaMetadataBootstrapSuccessStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaMetadataBootstrapSuccessRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M052 success record cannot enable launch or billable action")
        if self.ssh_attempted or self.remote_command_attempted:
            raise ValueError("metadata bootstrap success record cannot include remote execution")
        if self.package_install_attempted or self.training_attempted:
            raise ValueError("metadata bootstrap success record cannot include install/training")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_metadata_bootstrap_success_record_from_paths(
    *,
    workdir: str | Path,
    post_discovery: str | Path,
) -> LambdaMetadataBootstrapSuccessRecord:
    workdir_path = Path(workdir)
    post_discovery_path = Path(post_discovery)
    report = load_lambda_m029_report(workdir_path / "report.json")
    discovery = load_lambda_live_discovery_report(post_discovery_path)
    spend_path = workdir_path / "spend-audit.json"
    spend = (
        LambdaM029SpendAuditReport.model_validate_json(
            spend_path.read_text(encoding="utf-8")
        )
        if spend_path.exists()
        else None
    )
    conservative = None if spend is None else spend.estimated_spend
    final_instance_count = len(discovery.instances)
    final_unmanaged_count = len(discovery.unmanaged_instances)
    blockers: list[str] = []
    if not report.metadata_bootstrap_path_used or report.metadata_only is not True:
        blockers.append("metadata_bootstrap_path_not_confirmed")
    if not report.launch_request_sent:
        blockers.append("launch_request_not_sent")
    if not report.launch_response_received:
        blockers.append("launch_response_not_received")
    if report.launch_response_http_status != 200:
        blockers.append("launch_status_not_success")
    if not report.owned_instance_id_redacted:
        blockers.append("owned_instance_id_missing")
    if not report.readonly_verify_running_result:
        blockers.append("readonly_running_verification_missing")
    if not report.metadata_collected:
        blockers.append("metadata_collected_missing")
    if report.ssh_attempted:
        blockers.append("ssh_attempted")
    if report.remote_command_attempted:
        blockers.append("remote_command_attempted")
    if report.package_install_attempted:
        blockers.append("package_install_attempted")
    if report.training_attempted:
        blockers.append("training_attempted")
    if not report.termination_request_sent:
        blockers.append("termination_request_not_sent")
    if not report.termination_response_received:
        blockers.append("termination_response_not_received")
    if not report.termination_verified:
        blockers.append("termination_not_verified")
    if report.manual_review_required:
        blockers.append("manual_review_required")
    if final_instance_count != 0:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count != 0:
        blockers.append("final_unmanaged_count_nonzero")
    if report.estimated_spend >= 50 or (conservative is not None and conservative >= 50):
        blockers.append("estimated_spend_not_below_budget")
    if not discovery.secret_redacted:
        blockers.append("secret_scan_not_passed")
    status: LambdaMetadataBootstrapSuccessStatus = (
        "metadata_bootstrap_success"
        if not blockers
        else (
            "metadata_bootstrap_partial"
            if report.launch_request_sent and report.termination_request_sent
            else "metadata_bootstrap_failed"
        )
    )
    return LambdaMetadataBootstrapSuccessRecord(
        run_id=report.run_id,
        source_workdir=str(workdir_path),
        post_discovery_path=str(post_discovery_path),
        selected_candidate=report.selected_shape or report.selected_candidate,
        selected_region=report.selected_region,
        launch_request_sent=report.launch_request_sent,
        launch_response_received=report.launch_response_received,
        launch_status_code=report.launch_response_http_status,
        launch_content_type=report.launch_response_content_type,
        launch_body_size=report.launch_response_body_size_bytes,
        launch_response_classification=report.launch_response_classification,
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        readonly_verify_running_result=report.readonly_verify_running_result,
        metadata_collected=report.metadata_collected,
        ssh_attempted=report.ssh_attempted,
        remote_command_attempted=report.remote_command_attempted,
        package_install_attempted=report.package_install_attempted,
        training_attempted=report.training_attempted,
        termination_request_sent=report.termination_request_sent,
        termination_response_received=report.termination_response_received,
        termination_status_code=report.termination_response_http_status,
        termination_content_type=report.termination_response_content_type,
        termination_body_size=report.termination_response_body_size_bytes,
        readonly_verify_terminated_result=report.readonly_verify_terminated_result,
        termination_verified=report.termination_verified,
        manual_review_required=report.manual_review_required,
        mutating_operations=report.mutating_operations,
        historical_billable_action_performed=report.billable_action_performed,
        elapsed_seconds=report.elapsed_seconds,
        estimated_spend=report.estimated_spend,
        conservative_estimated_spend=conservative,
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        secret_scan_passed=discovery.secret_redacted,
        status=status,
        blockers=sorted(set(blockers)),
        warnings=[
            "M052 records historical M051B billable action only",
            "metadata bootstrap success is provider/API metadata only",
        ],
    )


def load_lambda_metadata_bootstrap_success_record(
    path: str | Path,
) -> LambdaMetadataBootstrapSuccessRecord:
    return LambdaMetadataBootstrapSuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_metadata_bootstrap_success_record(
    path: str | Path,
    record: LambdaMetadataBootstrapSuccessRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
