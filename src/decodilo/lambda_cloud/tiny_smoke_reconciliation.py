"""M073R2 remote Decodilo tiny-smoke reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.tiny_smoke_success_record import (
    load_lambda_tiny_smoke_success_record,
)


class LambdaTinySmokeReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074"
    reconciliation_passed: bool
    owned_instance_final_state: str = "absent_or_terminated"
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    no_unapproved_file_transfer: bool
    no_training: bool
    no_downloads: bool
    no_internet_install: bool
    local_only_dependency_install_confirmed: bool
    tiny_smoke_command_passed: bool
    artifact_metadata_confirmed: bool
    termination_verified: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_reconciliation(self) -> LambdaTinySmokeReconciliation:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M074 reconciliation must remain offline and disabled")
        if self.reconciliation_passed and self.errors:
            raise ValueError("passing reconciliation cannot carry errors")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_tiny_smoke_reconciliation_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaTinySmokeReconciliation:
    record = load_lambda_tiny_smoke_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    no_extra_transfer = (
        record.no_unapproved_file_transfer
        and bool(report.get("source_bundle_upload_succeeded"))
        and bool(report.get("dependency_bundle_upload_succeeded"))
        and not bool(report.get("unapproved_file_transfer_attempted"))
    )
    artifact_metadata_confirmed = (
        record.tiny_smoke_artifact_created
        and record.artifact_bounded
        and record.artifact_secret_scan_passed
        and record.artifact_sha256 is not None
    )
    errors: list[str] = []
    if record.status != "tiny_smoke_success":
        errors.append("success_record_not_success")
    if record.final_instance_count not in {0, None}:
        errors.append("final_instance_count_nonzero")
    if record.final_unmanaged_count not in {0, None}:
        errors.append("final_unmanaged_count_nonzero")
    if not no_extra_transfer:
        errors.append("unapproved_file_transfer_detected")
    if not record.no_real_training:
        errors.append("training_detected")
    if not record.no_downloads:
        errors.append("download_detected")
    if not record.no_internet_install:
        errors.append("internet_install_detected")
    if not record.local_only_dependency_install_passed:
        errors.append("local_dependency_install_not_confirmed")
    if not record.tiny_smoke_command_passed:
        errors.append("tiny_smoke_command_not_passed")
    if not artifact_metadata_confirmed:
        errors.append("artifact_metadata_not_confirmed")
    if not record.termination_verified:
        errors.append("termination_not_verified")

    return LambdaTinySmokeReconciliation(
        reconciliation_passed=not errors,
        final_instance_count=record.final_instance_count,
        final_unmanaged_count=record.final_unmanaged_count,
        no_unapproved_file_transfer=no_extra_transfer,
        no_training=record.no_real_training,
        no_downloads=record.no_downloads,
        no_internet_install=record.no_internet_install,
        local_only_dependency_install_confirmed=record.local_only_dependency_install_passed,
        tiny_smoke_command_passed=record.tiny_smoke_command_passed,
        artifact_metadata_confirmed=artifact_metadata_confirmed,
        termination_verified=record.termination_verified,
        warnings=["M074 reconciliation uses persisted M073R2 artifacts only"],
        errors=errors,
    )


def load_lambda_tiny_smoke_reconciliation(path: str | Path) -> LambdaTinySmokeReconciliation:
    return LambdaTinySmokeReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_smoke_reconciliation(
    path: str | Path,
    report: LambdaTinySmokeReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
