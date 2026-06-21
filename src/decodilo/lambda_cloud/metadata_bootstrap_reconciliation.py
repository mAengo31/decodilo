"""Post-run reconciliation for M051B metadata-only Lambda bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    load_lambda_metadata_bootstrap_success_record,
)

_BILLABLE_STATES = {"booting", "pending", "running", "active", "stopping", "unknown"}


class LambdaMetadataBootstrapReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    source_workdir: str
    post_discovery_path: str
    owned_instance_id_redacted: str | None = None
    owned_instance_final_state: str | None = None
    termination_verified: bool
    final_instance_count: int
    final_unmanaged_count: int
    billable_state_remaining_count: int
    unmanaged_billable_count: int
    metadata_only_confirmed: bool
    no_ssh_confirmed: bool
    no_remote_command_confirmed: bool
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
    def _validate_closeout_only(self) -> LambdaMetadataBootstrapReconciliation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M052 reconciliation cannot enable launch or billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_metadata_bootstrap_reconciliation_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
    post_discovery: str | Path,
) -> LambdaMetadataBootstrapReconciliation:
    workdir_path = Path(workdir)
    post_discovery_path = Path(post_discovery)
    report = load_lambda_m029_report(workdir_path / "report.json")
    success = load_lambda_metadata_bootstrap_success_record(success_record)
    discovery = load_lambda_live_discovery_report(post_discovery_path)
    errors: list[str] = []
    if not (workdir_path / "ledger.json").exists():
        errors.append("ledger_missing")
    if not (workdir_path / "journal.jsonl").exists():
        errors.append("journal_missing")
    if not (workdir_path / "spend-audit.json").exists():
        errors.append("spend_audit_missing")
    billable_remaining = sum(
        1 for instance in discovery.instances if instance.status in _BILLABLE_STATES
    )
    unmanaged_ids = set(discovery.unmanaged_instances)
    unmanaged_billable = sum(
        1
        for instance in discovery.instances
        if instance.status in _BILLABLE_STATES and instance.instance_id in unmanaged_ids
    )
    if success.status != "metadata_bootstrap_success":
        errors.append("success_record_not_success")
    if not report.metadata_bootstrap_path_used or report.metadata_only is not True:
        errors.append("metadata_only_not_confirmed")
    if report.ssh_attempted:
        errors.append("ssh_attempted")
    if report.remote_command_attempted:
        errors.append("remote_command_attempted")
    if report.package_install_attempted:
        errors.append("package_install_attempted")
    if report.training_attempted:
        errors.append("training_attempted")
    if not report.termination_verified:
        errors.append("termination_not_verified")
    if len(discovery.instances) != 0:
        errors.append("final_discovery_visible_instances_present")
    if len(discovery.unmanaged_instances) != 0:
        errors.append("final_discovery_unmanaged_instances_present")
    if billable_remaining:
        errors.append("billable_state_remaining")
    return LambdaMetadataBootstrapReconciliation(
        source_workdir=str(workdir_path),
        post_discovery_path=str(post_discovery_path),
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        owned_instance_final_state=report.readonly_verify_terminated_result,
        termination_verified=report.termination_verified,
        final_instance_count=len(discovery.instances),
        final_unmanaged_count=len(discovery.unmanaged_instances),
        billable_state_remaining_count=billable_remaining,
        unmanaged_billable_count=unmanaged_billable,
        metadata_only_confirmed=report.metadata_bootstrap_path_used
        and report.metadata_only is True,
        no_ssh_confirmed=not report.ssh_attempted,
        no_remote_command_confirmed=not report.remote_command_attempted,
        no_package_install_confirmed=not report.package_install_attempted,
        no_training_confirmed=not report.training_attempted,
        reconciliation_passed=not errors,
        warnings=["M052 reconciliation is offline and reads persisted M051B artifacts only"],
        errors=sorted(set(errors)),
    )


def load_lambda_metadata_bootstrap_reconciliation(
    path: str | Path,
) -> LambdaMetadataBootstrapReconciliation:
    return LambdaMetadataBootstrapReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_metadata_bootstrap_reconciliation(
    path: str | Path,
    report: LambdaMetadataBootstrapReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
