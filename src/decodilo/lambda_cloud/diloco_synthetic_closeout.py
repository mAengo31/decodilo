"""M081R2 DiLoCo-shaped synthetic closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_evidence_package import (
    load_lambda_diloco_synthetic_evidence_package,
)
from decodilo.lambda_cloud.diloco_synthetic_reconciliation import (
    load_lambda_diloco_synthetic_reconciliation,
)
from decodilo.lambda_cloud.diloco_synthetic_success_record import (
    load_lambda_diloco_synthetic_success_record,
)

LambdaDilocoSyntheticCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaDilocoSyntheticCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082"
    closeout_status: LambdaDilocoSyntheticCloseoutStatus
    closeout_succeeded: bool
    diloco_synthetic_success: bool
    reconciliation_passed: bool
    evidence_complete: bool
    artifact_auditable: bool
    artifact_body_persisted: bool
    parsed_summary_persisted: bool
    optimizer_claim_honesty_confirmed: bool
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    no_internet_install: bool
    no_downloads: bool
    no_real_training: bool
    no_unapproved_file_transfer: bool
    historical_billable_action_performed: bool
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_closeout(self) -> LambdaDilocoSyntheticCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M082 closeout must not enable launch or spend")
        if self.closeout_succeeded and self.closeout_status == "unresolved":
            raise ValueError("unresolved closeout cannot be marked succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_synthetic_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
) -> LambdaDilocoSyntheticCloseout:
    record = load_lambda_diloco_synthetic_success_record(success_record)
    reconcile = load_lambda_diloco_synthetic_reconciliation(reconciliation)
    package = load_lambda_diloco_synthetic_evidence_package(evidence_package)
    blockers: list[str] = []
    if record.success_status != "remote_diloco_shaped_synthetic_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not package.evidence_complete:
        blockers.append("evidence_package_not_complete")
    if not record.artifact_body_persisted:
        blockers.append("artifact_body_not_persisted")
    if not record.parsed_summary_persisted:
        blockers.append("parsed_summary_not_persisted")
    if not reconcile.optimizer_claim_honesty_confirmed:
        blockers.append("optimizer_claim_honesty_not_confirmed")
    if not record.termination_verified:
        blockers.append("termination_not_verified")
    if record.final_instance_count not in {0, None}:
        blockers.append("final_instance_count_nonzero")
    if record.final_unmanaged_count not in {0, None}:
        blockers.append("final_unmanaged_count_nonzero")
    for name, value in {
        "internet_install": record.no_internet_install,
        "downloads": record.no_downloads,
        "real_training": record.no_real_training,
        "unapproved_file_transfer": record.no_unapproved_file_transfer,
    }.items():
        if not value:
            blockers.append(f"{name}_detected")
    closeout_succeeded = not blockers
    warnings = [
        "M082 is offline; historical M081R2 billable action remains recorded separately",
        "M081R2 is a DiLoCo-shaped protocol baseline, not full optimizer fidelity",
    ]
    if closeout_succeeded and (record.warnings or package.warnings):
        status: LambdaDilocoSyntheticCloseoutStatus = "closed_with_warnings"
    elif closeout_succeeded:
        status = "closed_success"
    else:
        status = "unresolved"
    return LambdaDilocoSyntheticCloseout(
        closeout_status=status,
        closeout_succeeded=closeout_succeeded,
        diloco_synthetic_success=(
            record.success_status == "remote_diloco_shaped_synthetic_success"
        ),
        reconciliation_passed=reconcile.reconciliation_passed,
        evidence_complete=package.evidence_complete,
        artifact_auditable=record.artifact_path is not None,
        artifact_body_persisted=record.artifact_body_persisted,
        parsed_summary_persisted=record.parsed_summary_persisted,
        optimizer_claim_honesty_confirmed=reconcile.optimizer_claim_honesty_confirmed,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        termination_verified=record.termination_verified,
        final_instance_count=record.final_instance_count,
        final_unmanaged_count=record.final_unmanaged_count,
        no_internet_install=record.no_internet_install,
        no_downloads=record.no_downloads,
        no_real_training=record.no_real_training,
        no_unapproved_file_transfer=record.no_unapproved_file_transfer,
        historical_billable_action_performed=record.historical_billable_action_performed,
        warnings=warnings,
        blockers=blockers,
    )


def load_lambda_diloco_synthetic_closeout(
    path: str | Path,
) -> LambdaDilocoSyntheticCloseout:
    return LambdaDilocoSyntheticCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_closeout(
    path: str | Path,
    report: LambdaDilocoSyntheticCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
