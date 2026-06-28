"""Closeout for the successful M063 GPU visibility query run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_evidence_package import (
    load_lambda_gpu_visibility_evidence_package,
)
from decodilo.lambda_cloud.gpu_visibility_parsed_output_audit import (
    load_lambda_gpu_visibility_parsed_output_audit,
)
from decodilo.lambda_cloud.gpu_visibility_reconciliation import (
    load_lambda_gpu_visibility_reconciliation,
)
from decodilo.lambda_cloud.gpu_visibility_success_record import (
    load_lambda_gpu_visibility_success_record,
)

LambdaGPUVisibilityCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaGPUVisibilityCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    closeout_status: LambdaGPUVisibilityCloseoutStatus
    closeout_succeeded: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    owned_instance_id_redacted: str | None = None
    command: str
    command_category: str = "gpu_visibility_query"
    command_exit_code: int | None = None
    parsed_output_status: str
    parsed_fields_present: bool
    stdout_captured_redacted: bool
    raw_stdout_reported: bool
    termination_verified: bool
    manual_review_required: bool
    final_instance_count: int
    final_unmanaged_count: int
    secret_scan_passed: bool
    command_scope_respected: bool
    no_file_transfer_confirmed: bool
    no_port_forwarding_confirmed: bool
    no_package_install_confirmed: bool
    no_training_confirmed: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaGPUVisibilityCloseout:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M064 closeout cannot enable launch or mutation")
        if self.command_category != "gpu_visibility_query":
            raise ValueError("M064 closeout can only close GPU visibility query")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
    parsed_output_audit: str | Path,
) -> LambdaGPUVisibilityCloseout:
    success = load_lambda_gpu_visibility_success_record(success_record)
    reconcile = load_lambda_gpu_visibility_reconciliation(reconciliation)
    evidence = load_lambda_gpu_visibility_evidence_package(evidence_package)
    audit = load_lambda_gpu_visibility_parsed_output_audit(parsed_output_audit)
    blockers = [*success.blockers, *reconcile.errors, *evidence.blockers, *audit.blockers]
    if success.status not in {
        "gpu_visibility_query_success",
        "gpu_visibility_query_executed_output_hash_only",
    }:
        blockers.append("success_record_not_success_or_hash_only")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not evidence.evidence_complete:
        blockers.append("evidence_package_incomplete")
    if audit.parsed_output_audit_status == "missing_output":
        blockers.append("gpu_visibility_output_missing")
    if not success.secret_scan_passed:
        blockers.append("secret_scan_not_passed")
    if success.final_instance_count != 0 or success.final_unmanaged_count != 0:
        blockers.append("final_visible_or_unmanaged_instances_present")
    if not success.termination_verified:
        blockers.append("termination_not_verified")
    if success.manual_review_required:
        blockers.append("manual_review_required")
    if success.raw_stdout_reported:
        blockers.append("raw_stdout_reported")
    if blockers:
        closeout_status: LambdaGPUVisibilityCloseoutStatus = "unresolved"
    elif audit.parsed_output_audit_status == "output_hash_only":
        closeout_status = "closed_with_warnings"
    elif success.warnings or reconcile.warnings or evidence.warnings or audit.warnings:
        closeout_status = "closed_with_warnings"
    else:
        closeout_status = "closed_success"
    warnings = sorted(
        set(
            [
                "M064 closeout is offline and performs no Lambda, SSH, or remote command operation",
                *success.warnings,
                *reconcile.warnings,
                *evidence.warnings,
                *audit.warnings,
            ]
        )
    )
    return LambdaGPUVisibilityCloseout(
        closeout_status=closeout_status,
        closeout_succeeded=not blockers,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        owned_instance_id_redacted=success.owned_instance_id_redacted,
        command=success.command,
        command_exit_code=success.command_exit_code,
        parsed_output_status=audit.parsed_output_audit_status,
        parsed_fields_present=success.parsed_fields_present,
        stdout_captured_redacted=success.stdout_redacted,
        raw_stdout_reported=success.raw_stdout_reported,
        termination_verified=success.termination_verified,
        manual_review_required=success.manual_review_required,
        final_instance_count=success.final_instance_count,
        final_unmanaged_count=success.final_unmanaged_count,
        secret_scan_passed=success.secret_scan_passed,
        command_scope_respected=reconcile.command_scope_respected,
        no_file_transfer_confirmed=reconcile.no_file_transfer_confirmed,
        no_port_forwarding_confirmed=reconcile.no_port_forwarding_confirmed,
        no_package_install_confirmed=reconcile.no_package_install_confirmed,
        no_training_confirmed=reconcile.no_training_confirmed,
        historical_billable_action_performed=success.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def load_lambda_gpu_visibility_closeout(path: str | Path) -> LambdaGPUVisibilityCloseout:
    return LambdaGPUVisibilityCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_closeout(
    path: str | Path,
    report: LambdaGPUVisibilityCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
