"""M083R DiLoCo optimizer-fidelity closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_evidence_package import (
    load_lambda_diloco_optimizer_evidence_package,
)
from decodilo.lambda_cloud.diloco_optimizer_reconciliation import (
    load_lambda_diloco_optimizer_reconciliation,
)
from decodilo.lambda_cloud.diloco_optimizer_success_record import (
    load_lambda_diloco_optimizer_success_record,
)

LambdaDilocoOptimizerCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaDilocoOptimizerCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084"
    closeout_status: LambdaDilocoOptimizerCloseoutStatus
    closeout_succeeded: bool
    diloco_optimizer_success: bool
    reconciliation_passed: bool
    evidence_complete: bool
    artifact_auditable: bool
    artifact_body_persisted: bool
    parsed_summary_persisted: bool
    optimizer_semantics_confirmed: bool
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    max_abs_error: float | None = None
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
    def _validate_closeout(self) -> LambdaDilocoOptimizerCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M084 closeout must not enable launch or spend")
        if self.closeout_succeeded and self.closeout_status == "unresolved":
            raise ValueError("unresolved closeout cannot be marked succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_optimizer_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
) -> LambdaDilocoOptimizerCloseout:
    record = load_lambda_diloco_optimizer_success_record(success_record)
    reconcile = load_lambda_diloco_optimizer_reconciliation(reconciliation)
    package = load_lambda_diloco_optimizer_evidence_package(evidence_package)
    blockers: list[str] = []
    if record.success_status != "remote_diloco_optimizer_smoke_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not package.evidence_complete:
        blockers.append("evidence_package_not_complete")
    if not record.artifact_body_persisted:
        blockers.append("artifact_body_not_persisted")
    if not record.parsed_summary_persisted:
        blockers.append("parsed_summary_not_persisted")
    if not reconcile.optimizer_semantics_confirmed:
        blockers.append("optimizer_semantics_not_confirmed")
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
        "M084 is offline; historical M083R billable action remains recorded separately",
        "M083R is an optimizer-fidelity smoke, not full DiLoCo training",
    ]
    if closeout_succeeded and (record.warnings or package.warnings):
        status: LambdaDilocoOptimizerCloseoutStatus = "closed_with_warnings"
    elif closeout_succeeded:
        status = "closed_success"
    else:
        status = "unresolved"
    return LambdaDilocoOptimizerCloseout(
        closeout_status=status,
        closeout_succeeded=closeout_succeeded,
        diloco_optimizer_success=(
            record.success_status == "remote_diloco_optimizer_smoke_success"
        ),
        reconciliation_passed=reconcile.reconciliation_passed,
        evidence_complete=package.evidence_complete,
        artifact_auditable=record.artifact_path is not None,
        artifact_body_persisted=record.artifact_body_persisted,
        parsed_summary_persisted=record.parsed_summary_persisted,
        optimizer_semantics_confirmed=reconcile.optimizer_semantics_confirmed,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        max_abs_error=record.max_abs_error,
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


def load_lambda_diloco_optimizer_closeout(
    path: str | Path,
) -> LambdaDilocoOptimizerCloseout:
    return LambdaDilocoOptimizerCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_optimizer_closeout(
    path: str | Path,
    report: LambdaDilocoOptimizerCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
