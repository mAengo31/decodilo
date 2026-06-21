"""Success record for the completed Lambda lifecycle smoke run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport

LambdaLifecycleSmokeSuccessStatus = Literal[
    "lifecycle_smoke_success",
    "lifecycle_smoke_partial",
    "lifecycle_smoke_failed",
]


class LambdaLifecycleSmokeSuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_schema_version: int = 1
    run_id: str
    milestone: str = "M046C"
    source_workdir: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    instance_type_name: str | None = None
    owned_instance_id_redacted: str | None = None
    launch_request_sent: bool
    launch_response_received: bool
    launch_status_code: int | None = None
    launch_response_classification: str | None = None
    readonly_verify_running_result: str | None = None
    termination_request_sent: bool
    termination_response_received: bool
    termination_status_code: int | None = None
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
    no_ssh: bool = True
    no_setup_scripts: bool = True
    no_cloud_init: bool = True
    no_training: bool = True
    no_restart: bool = True
    no_create_delete_resources: bool = True
    secret_scan_passed: bool
    status: LambdaLifecycleSmokeSuccessStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_m047_no_new_action(self) -> LambdaLifecycleSmokeSuccessRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("success record cannot enable launch or record new billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lifecycle_smoke_success_record_from_paths(
    *,
    workdir: str | Path,
    final_summary: str | Path,
    post_discovery: str | Path,
) -> LambdaLifecycleSmokeSuccessRecord:
    workdir_path = Path(workdir)
    report = load_lambda_m029_report(workdir_path / "report.json")
    summary = json.loads(Path(final_summary).read_text(encoding="utf-8"))
    discovery = load_lambda_live_discovery_report(post_discovery)
    spend_path = workdir_path / "spend-audit.json"
    spend = (
        LambdaM029SpendAuditReport.model_validate_json(spend_path.read_text(encoding="utf-8"))
        if spend_path.exists()
        else None
    )
    conservative = (
        spend.estimated_spend
        if spend is not None
        else summary.get("spend_audit", {}).get("estimated_spend")
    )
    secret_scan_findings = summary.get("secret_scan_findings", {})
    final_instance_count = len(discovery.instances)
    final_unmanaged_count = len(discovery.unmanaged_instances)
    blockers: list[str] = []
    if not report.launch_request_sent:
        blockers.append("launch_request_not_sent")
    if not report.launch_response_received:
        blockers.append("launch_response_not_received")
    if not report.owned_instance_id_redacted:
        blockers.append("owned_instance_id_missing")
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
    if secret_scan_findings:
        blockers.append("secret_scan_findings_present")
    status: LambdaLifecycleSmokeSuccessStatus = (
        "lifecycle_smoke_success"
        if not blockers
        else (
            "lifecycle_smoke_partial"
            if report.launch_request_sent and report.termination_request_sent
            else "lifecycle_smoke_failed"
        )
    )
    return LambdaLifecycleSmokeSuccessRecord(
        run_id=report.run_id,
        source_workdir=str(workdir_path),
        selected_candidate=report.selected_candidate,
        selected_region=report.selected_region,
        instance_type_name=report.selected_shape or report.selected_candidate,
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        launch_request_sent=report.launch_request_sent,
        launch_response_received=report.launch_response_received,
        launch_status_code=report.launch_response_http_status,
        launch_response_classification=report.launch_response_classification,
        readonly_verify_running_result=report.readonly_verify_running_result,
        termination_request_sent=report.termination_request_sent,
        termination_response_received=report.termination_response_received,
        termination_status_code=report.termination_response_http_status,
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
        secret_scan_passed=not secret_scan_findings,
        status=status,
        blockers=sorted(set(blockers)),
        warnings=["M047 records historical M046C billable action only"],
    )


def load_lambda_lifecycle_smoke_success_record(
    path: str | Path,
) -> LambdaLifecycleSmokeSuccessRecord:
    return LambdaLifecycleSmokeSuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lifecycle_smoke_success_record(
    path: str | Path,
    record: LambdaLifecycleSmokeSuccessRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
