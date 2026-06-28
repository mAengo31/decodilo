"""Closeout for the successful M059 hostname identity command run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_hostname_identity_evidence_package import (
    load_lambda_ssh_hostname_identity_evidence_package,
)
from decodilo.lambda_cloud.ssh_hostname_identity_reconciliation import (
    load_lambda_ssh_hostname_identity_reconciliation,
)
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    load_lambda_ssh_hostname_identity_success_record,
)

LambdaSSHHostnameIdentityCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaSSHHostnameIdentityCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    closeout_status: LambdaSSHHostnameIdentityCloseoutStatus
    closeout_succeeded: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    owned_instance_id_redacted: str | None = None
    command: str = "hostname"
    command_category: str = "identity_hostname"
    command_exit_code: int | None = None
    stdout_captured_redacted: bool
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
    def _validate_closeout_only(self) -> LambdaSSHHostnameIdentityCloseout:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M060 closeout cannot enable launch or mutation")
        if self.command != "hostname" or self.command_category != "identity_hostname":
            raise ValueError("M060 closeout can only close hostname")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_hostname_identity_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
) -> LambdaSSHHostnameIdentityCloseout:
    success = load_lambda_ssh_hostname_identity_success_record(success_record)
    reconcile = load_lambda_ssh_hostname_identity_reconciliation(reconciliation)
    evidence = load_lambda_ssh_hostname_identity_evidence_package(evidence_package)
    blockers = [*success.blockers, *reconcile.errors, *evidence.blockers]
    if success.status != "ssh_hostname_identity_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not evidence.evidence_complete:
        blockers.append("evidence_package_incomplete")
    if not success.secret_scan_passed:
        blockers.append("secret_scan_not_passed")
    if success.final_instance_count != 0 or success.final_unmanaged_count != 0:
        blockers.append("final_visible_or_unmanaged_instances_present")
    if not success.termination_verified:
        blockers.append("termination_not_verified")
    if success.manual_review_required:
        blockers.append("manual_review_required")
    if blockers:
        closeout_status: LambdaSSHHostnameIdentityCloseoutStatus = "unresolved"
    elif success.warnings or reconcile.warnings or evidence.warnings:
        closeout_status = "closed_with_warnings"
    else:
        closeout_status = "closed_success"
    return LambdaSSHHostnameIdentityCloseout(
        closeout_status=closeout_status,
        closeout_succeeded=not blockers,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        owned_instance_id_redacted=success.owned_instance_id_redacted,
        command_exit_code=success.command_exit_code,
        stdout_captured_redacted=success.stdout_captured_redacted,
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
        warnings=sorted(
            set(
                [
                    "M060 closeout is offline and performs no Lambda operation",
                    *success.warnings,
                    *reconcile.warnings,
                    *evidence.warnings,
                ]
            )
        ),
    )


def load_lambda_ssh_hostname_identity_closeout(
    path: str | Path,
) -> LambdaSSHHostnameIdentityCloseout:
    return LambdaSSHHostnameIdentityCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_hostname_identity_closeout(
    path: str | Path,
    report: LambdaSSHHostnameIdentityCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
