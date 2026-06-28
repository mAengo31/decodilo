"""M081R2 DiLoCo-shaped synthetic reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_success_record import (
    load_lambda_diloco_synthetic_success_record,
)


class LambdaDilocoSyntheticReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082"
    reconciliation_passed: bool
    owned_instance_final_state: str = "absent_or_terminated"
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    no_unapproved_file_transfer: bool
    no_training: bool
    no_downloads: bool
    no_internet_install: bool
    local_only_dependency_install_confirmed: bool
    diloco_smoke_command_passed: bool
    artifact_metadata_confirmed: bool
    artifact_body_confirmed: bool
    optimizer_claim_honesty_confirmed: bool
    termination_verified: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_reconciliation(self) -> LambdaDilocoSyntheticReconciliation:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M082 reconciliation must remain offline and disabled")
        if self.reconciliation_passed and self.errors:
            raise ValueError("passing reconciliation cannot carry errors")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_synthetic_reconciliation_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaDilocoSyntheticReconciliation:
    record = load_lambda_diloco_synthetic_success_record(success_record)
    report = json.loads((Path(workdir) / "report.json").read_text(encoding="utf-8"))
    no_extra_transfer = (
        record.no_unapproved_file_transfer
        and bool(report.get("source_bundle_upload_succeeded"))
        and bool(report.get("dependency_bundle_upload_succeeded"))
        and not bool(report.get("unapproved_file_transfer_attempted"))
    )
    artifact_metadata_confirmed = (
        record.artifact_path is not None
        and record.artifact_bounded
        and record.artifact_secret_scan_passed
        and record.artifact_sha256 is not None
    )
    artifact_body_confirmed = (
        record.artifact_body_persisted and record.parsed_summary_persisted
    )
    optimizer_claim_honesty = (
        record.optimization_fidelity == "diloco_shaped_protocol_only"
        and record.inner_optimizer_semantics == "synthetic_placeholder"
        and record.outer_optimizer_semantics == "token_weighted_merge"
        and record.parameter_fragment_semantics == "not_exercised"
    )
    errors: list[str] = []
    if record.success_status != "remote_diloco_shaped_synthetic_success":
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
    if not record.dependency_install_passed:
        errors.append("local_dependency_install_not_confirmed")
    if not record.diloco_smoke_command_passed:
        errors.append("diloco_smoke_command_not_passed")
    if not artifact_metadata_confirmed:
        errors.append("artifact_metadata_not_confirmed")
    if not artifact_body_confirmed:
        errors.append("artifact_body_not_confirmed")
    if not optimizer_claim_honesty:
        errors.append("optimizer_claim_honesty_not_confirmed")
    if not record.termination_verified:
        errors.append("termination_not_verified")
    return LambdaDilocoSyntheticReconciliation(
        reconciliation_passed=not errors,
        final_instance_count=record.final_instance_count,
        final_unmanaged_count=record.final_unmanaged_count,
        no_unapproved_file_transfer=no_extra_transfer,
        no_training=record.no_real_training,
        no_downloads=record.no_downloads,
        no_internet_install=record.no_internet_install,
        local_only_dependency_install_confirmed=record.dependency_install_passed,
        diloco_smoke_command_passed=record.diloco_smoke_command_passed,
        artifact_metadata_confirmed=artifact_metadata_confirmed,
        artifact_body_confirmed=artifact_body_confirmed,
        optimizer_claim_honesty_confirmed=optimizer_claim_honesty,
        termination_verified=record.termination_verified,
        warnings=["M082 reconciliation uses persisted M081R2 artifacts only"],
        errors=errors,
    )


def load_lambda_diloco_synthetic_reconciliation(
    path: str | Path,
) -> LambdaDilocoSyntheticReconciliation:
    return LambdaDilocoSyntheticReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_reconciliation(
    path: str | Path,
    report: LambdaDilocoSyntheticReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
