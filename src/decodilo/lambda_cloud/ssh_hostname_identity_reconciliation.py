"""Offline reconciliation for the completed M059 hostname identity command run."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    load_lambda_ssh_hostname_identity_success_record,
)

_BILLABLE_STATES = {"booting", "pending", "running", "active", "stopping", "unknown"}


class LambdaSSHHostnameIdentityReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    source_workdir: str
    final_discovery_path: str
    owned_instance_id_redacted: str | None = None
    owned_instance_final_state: str | None = None
    termination_verified: bool
    final_instance_count: int
    final_unmanaged_count: int
    billable_state_remaining_count: int
    unmanaged_billable_count: int
    command_scope_respected: bool
    stdout_redacted_confirmed: bool
    no_file_transfer_confirmed: bool
    no_port_forwarding_confirmed: bool
    no_package_install_confirmed: bool
    no_training_confirmed: bool
    reconciliation_passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaSSHHostnameIdentityReconciliation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M060 reconciliation cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_hostname_identity_reconciliation_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
    final_discovery: str | Path | None = None,
) -> LambdaSSHHostnameIdentityReconciliation:
    workdir_path = Path(workdir)
    success = load_lambda_ssh_hostname_identity_success_record(success_record)
    discovery_path = Path(final_discovery or success.final_discovery_path)
    report = load_lambda_m029_report(workdir_path / "report.json")
    discovery = load_lambda_live_discovery_report(discovery_path)
    evidence_path = workdir_path / "ssh-connectivity-evidence.json"
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.exists()
        else {}
    )
    errors: list[str] = []
    for name in ("ledger.json", "journal.jsonl", "spend-audit.json", "report.json"):
        if not (workdir_path / name).exists():
            errors.append(f"{name.replace('.', '_')}_missing")
    billable_remaining = sum(
        1 for instance in discovery.instances if instance.status in _BILLABLE_STATES
    )
    unmanaged_ids = set(discovery.unmanaged_instances)
    unmanaged_billable = sum(
        1
        for instance in discovery.instances
        if instance.status in _BILLABLE_STATES and instance.instance_id in unmanaged_ids
    )
    stdout_redacted = (
        report.stdout_redacted_present
        and evidence.get("stdout_redacted") == "<redacted-hostname>"
        and evidence.get("stdout_stored") is False
        and report.stdout_secret_scan_passed is True
    )
    command_scope_respected = (
        success.status == "ssh_hostname_identity_success"
        and report.remote_command_attempted
        and report.remote_command == "hostname"
        and report.remote_command_result == "succeeded"
        and report.ssh_exit_status == 0
        and evidence.get("approved_command") == "hostname"
        and evidence.get("command_output_collected") is True
        and stdout_redacted
    )
    if not command_scope_respected:
        errors.append("command_scope_not_respected")
    if not stdout_redacted:
        errors.append("stdout_not_redacted")
    if not report.termination_verified:
        errors.append("termination_not_verified")
    if len(discovery.instances) != 0:
        errors.append("final_discovery_visible_instances_present")
    if len(discovery.unmanaged_instances) != 0:
        errors.append("final_discovery_unmanaged_instances_present")
    if billable_remaining:
        errors.append("billable_state_remaining")
    if report.file_transfer_attempted:
        errors.append("file_transfer_attempted")
    if report.port_forwarding_attempted:
        errors.append("port_forwarding_attempted")
    if report.package_install_attempted:
        errors.append("package_install_attempted")
    if report.training_attempted:
        errors.append("training_attempted")
    return LambdaSSHHostnameIdentityReconciliation(
        source_workdir=str(workdir_path),
        final_discovery_path=str(discovery_path),
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        owned_instance_final_state=report.readonly_verify_terminated_result,
        termination_verified=report.termination_verified,
        final_instance_count=len(discovery.instances),
        final_unmanaged_count=len(discovery.unmanaged_instances),
        billable_state_remaining_count=billable_remaining,
        unmanaged_billable_count=unmanaged_billable,
        command_scope_respected=command_scope_respected,
        stdout_redacted_confirmed=stdout_redacted,
        no_file_transfer_confirmed=not report.file_transfer_attempted,
        no_port_forwarding_confirmed=not report.port_forwarding_attempted,
        no_package_install_confirmed=not report.package_install_attempted,
        no_training_confirmed=not report.training_attempted,
        reconciliation_passed=not errors,
        warnings=["M060 reconciliation is offline and reads persisted M059 artifacts only"],
        errors=sorted(set(errors)),
    )


def load_lambda_ssh_hostname_identity_reconciliation(
    path: str | Path,
) -> LambdaSSHHostnameIdentityReconciliation:
    return LambdaSSHHostnameIdentityReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_hostname_identity_reconciliation(
    path: str | Path,
    report: LambdaSSHHostnameIdentityReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
