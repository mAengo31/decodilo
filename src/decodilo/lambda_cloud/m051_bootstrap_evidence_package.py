"""Post-run evidence package for M051 metadata-only Lambda bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bootstrap_evidence_schema import (
    load_lambda_bootstrap_evidence_schema,
)
from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport


class LambdaM051BootstrapEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_complete: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    owned_instance_id_redacted: str | None = None
    metadata_collected: dict[str, object] = Field(default_factory=dict)
    ssh_attempted: bool = False
    remote_command_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    termination_verified: bool
    manual_review_required: bool
    final_instance_count: int
    final_unmanaged_count: int
    estimated_spend: float
    conservative_estimated_spend: float | None = None
    secret_scan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM051BootstrapEvidencePackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_attempted
            or self.remote_command_attempted
            or self.package_install_attempted
            or self.training_attempted
        ):
            raise ValueError("M051 evidence package cannot record forbidden work")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_bootstrap_evidence_package_from_paths(
    *,
    workdir: str | Path,
    evidence_schema: str | Path,
    post_discovery: str | Path,
) -> LambdaM051BootstrapEvidencePackage:
    workdir_path = Path(workdir)
    schema = load_lambda_bootstrap_evidence_schema(evidence_schema)
    report = load_lambda_m029_report(workdir_path / "report.json")
    discovery = load_lambda_live_discovery_report(post_discovery)
    spend_path = workdir_path / "spend-audit.json"
    spend = (
        LambdaM029SpendAuditReport.model_validate_json(
            spend_path.read_text(encoding="utf-8")
        )
        if spend_path.exists()
        else None
    )
    blockers: list[str] = []
    if not schema.schema_valid:
        blockers.append("bootstrap_evidence_schema_invalid")
    if not report.launch_request_sent:
        blockers.append("launch_request_not_sent")
    if report.ssh_attempted:
        blockers.append("ssh_attempted")
    if report.remote_command_attempted:
        blockers.append("remote_command_attempted")
    if report.package_install_attempted:
        blockers.append("package_install_attempted")
    if report.training_attempted:
        blockers.append("training_attempted")
    if report.owned_instance_id_redacted and not report.termination_verified:
        blockers.append("owned_instance_termination_not_verified")
    if len(discovery.instances) != 0:
        blockers.append("final_instance_count_nonzero")
    if len(discovery.unmanaged_instances) != 0:
        blockers.append("final_unmanaged_count_nonzero")
    if report.estimated_spend >= 50:
        blockers.append("estimated_spend_not_below_budget")

    metadata_collected = {
        "instance_type": report.selected_shape or report.selected_candidate,
        "region": report.selected_region,
        "owned_instance_id_redacted": report.owned_instance_id_redacted,
        "running_verification": report.readonly_verify_running_result,
        "termination_verification": report.readonly_verify_terminated_result,
        "price_estimate": report.estimated_spend,
    }
    return LambdaM051BootstrapEvidencePackage(
        evidence_complete=not blockers,
        selected_candidate=report.selected_shape or report.selected_candidate,
        selected_region=report.selected_region,
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        metadata_collected=metadata_collected,
        ssh_attempted=bool(report.ssh_attempted),
        remote_command_attempted=bool(report.remote_command_attempted),
        package_install_attempted=bool(report.package_install_attempted),
        training_attempted=bool(report.training_attempted),
        termination_verified=report.termination_verified,
        manual_review_required=report.manual_review_required,
        final_instance_count=len(discovery.instances),
        final_unmanaged_count=len(discovery.unmanaged_instances),
        estimated_spend=report.estimated_spend,
        conservative_estimated_spend=None if spend is None else spend.estimated_spend,
        secret_scan_passed=discovery.secret_redacted,
        blockers=sorted(set(blockers)),
        warnings=[
            "M051 evidence package contains provider/API metadata only",
            "No SSH or remote command evidence is expected in metadata-only mode",
        ],
    )


def load_lambda_m051_bootstrap_evidence_package(
    path: str | Path,
) -> LambdaM051BootstrapEvidencePackage:
    return LambdaM051BootstrapEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_bootstrap_evidence_package(
    path: str | Path,
    report: LambdaM051BootstrapEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
