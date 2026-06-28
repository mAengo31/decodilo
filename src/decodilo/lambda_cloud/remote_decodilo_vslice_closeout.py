"""M069R remote Decodilo vertical-slice closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_decodilo_vslice_evidence_package import (
    load_lambda_remote_decodilo_vslice_evidence_package,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_reconciliation import (
    load_lambda_remote_decodilo_vslice_reconciliation,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    load_lambda_remote_decodilo_vslice_success_record,
)

LambdaRemoteDecodiloVSliceCloseoutStatus = Literal[
    "closed_success",
    "closed_with_warnings",
    "unresolved",
]


class LambdaRemoteDecodiloVSliceCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M070"
    closeout_status: LambdaRemoteDecodiloVSliceCloseoutStatus
    closeout_succeeded: bool
    remote_decodilo_vslice_success: bool
    reconciliation_passed: bool
    evidence_complete: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    no_internet_install: bool
    no_downloads: bool
    no_training: bool
    no_extra_file_transfer: bool
    historical_billable_action_performed: bool
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_closeout(self) -> LambdaRemoteDecodiloVSliceCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M070 closeout must not enable launch or spend")
        if self.closeout_succeeded and self.closeout_status == "unresolved":
            raise ValueError("unresolved closeout cannot be marked succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_decodilo_vslice_closeout_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
) -> LambdaRemoteDecodiloVSliceCloseout:
    record = load_lambda_remote_decodilo_vslice_success_record(success_record)
    reconcile = load_lambda_remote_decodilo_vslice_reconciliation(reconciliation)
    package = load_lambda_remote_decodilo_vslice_evidence_package(evidence_package)
    blockers: list[str] = []
    if record.status != "remote_decodilo_vslice_success":
        blockers.append("success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("reconciliation_not_passed")
    if not package.evidence_complete:
        blockers.append("evidence_package_not_complete")
    if not record.termination_verified:
        blockers.append("termination_not_verified")
    if record.final_instance_count not in {0, None}:
        blockers.append("final_instance_count_nonzero")
    if record.final_unmanaged_count not in {0, None}:
        blockers.append("final_unmanaged_count_nonzero")
    for name, value in {
        "internet_install": record.no_internet_install,
        "downloads": record.no_downloads,
        "training": record.no_training,
        "extra_file_transfer": record.no_extra_file_transfer,
    }.items():
        if not value:
            blockers.append(f"{name}_detected")
    closeout_succeeded = not blockers
    warnings = [
        "M070 is offline; historical M069R billable action remains recorded separately",
    ]
    status: LambdaRemoteDecodiloVSliceCloseoutStatus
    if closeout_succeeded and (record.warnings or package.warnings):
        status = "closed_with_warnings"
    elif closeout_succeeded:
        status = "closed_success"
    else:
        status = "unresolved"
    return LambdaRemoteDecodiloVSliceCloseout(
        closeout_status=status,
        closeout_succeeded=closeout_succeeded,
        remote_decodilo_vslice_success=record.status == "remote_decodilo_vslice_success",
        reconciliation_passed=reconcile.reconciliation_passed,
        evidence_complete=package.evidence_complete,
        termination_verified=record.termination_verified,
        final_instance_count=record.final_instance_count,
        final_unmanaged_count=record.final_unmanaged_count,
        no_internet_install=record.no_internet_install,
        no_downloads=record.no_downloads,
        no_training=record.no_training,
        no_extra_file_transfer=record.no_extra_file_transfer,
        historical_billable_action_performed=record.historical_billable_action_performed,
        warnings=warnings,
        blockers=blockers,
    )


def load_lambda_remote_decodilo_vslice_closeout(
    path: str | Path,
) -> LambdaRemoteDecodiloVSliceCloseout:
    return LambdaRemoteDecodiloVSliceCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_decodilo_vslice_closeout(
    path: str | Path,
    report: LambdaRemoteDecodiloVSliceCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
