"""Offline reconciliation for M067R remote vertical-slice attempts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_closeout import (
    load_lambda_remote_vertical_slice_closeout,
)


class LambdaRemoteVerticalSliceReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    owned_instance_final_state: str
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    bundle_upload_attempted: bool
    extra_file_transfer_attempted: bool
    remote_command_attempted: bool
    package_install_attempted: bool
    download_attempted: bool
    training_attempted: bool
    reconciliation_passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_execution(self) -> LambdaRemoteVerticalSliceReconciliation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M067S reconciliation cannot enable launch, mutation, or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vertical_slice_reconciliation_from_paths(
    *,
    workdir: str | Path,
    closeout: str | Path,
) -> LambdaRemoteVerticalSliceReconciliation:
    report = json.loads((Path(workdir) / "report.json").read_text(encoding="utf-8"))
    close = load_lambda_remote_vertical_slice_closeout(closeout)
    errors: list[str] = []
    if not close.termination_verified:
        errors.append("termination_not_verified")
    if close.final_instance_count != 0:
        errors.append("final_instance_count_not_zero")
    if close.final_unmanaged_count != 0:
        errors.append("final_unmanaged_count_not_zero")
    if bool(report.get("source_bundle_upload_attempted")):
        errors.append("bundle_upload_attempted_before_ssh_ready")
    if bool(report.get("file_transfer_attempted")):
        errors.append("extra_file_transfer_attempted")
    if bool(report.get("remote_command_attempted")):
        errors.append("remote_command_attempted")
    if bool(report.get("package_install_attempted")):
        errors.append("package_install_attempted")
    if bool(report.get("training_attempted")):
        errors.append("training_attempted")
    return LambdaRemoteVerticalSliceReconciliation(
        owned_instance_final_state=(
            "absent"
            if close.final_instance_count == 0 and close.final_unmanaged_count == 0
            else "visible_or_unresolved"
        ),
        termination_verified=close.termination_verified,
        final_instance_count=close.final_instance_count,
        final_unmanaged_count=close.final_unmanaged_count,
        bundle_upload_attempted=bool(report.get("source_bundle_upload_attempted")),
        extra_file_transfer_attempted=bool(report.get("file_transfer_attempted")),
        remote_command_attempted=bool(report.get("remote_command_attempted")),
        package_install_attempted=bool(report.get("package_install_attempted")),
        download_attempted=bool(report.get("download_attempted", False)),
        training_attempted=bool(report.get("training_attempted")),
        reconciliation_passed=not errors,
        errors=sorted(set(errors)),
        warnings=[
            "M067S reconciliation is offline and only reads completed M067R artifacts",
        ],
    )


def load_lambda_remote_vertical_slice_reconciliation(
    path: str | Path,
) -> LambdaRemoteVerticalSliceReconciliation:
    return LambdaRemoteVerticalSliceReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vertical_slice_reconciliation(
    path: str | Path,
    report: LambdaRemoteVerticalSliceReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
