"""Source and dependency bundle upload policy for M073R2."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.upload_readiness_policy import (
    load_lambda_upload_readiness_gate_policy,
)


class LambdaSourceDependencyUploadPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    upload_policy_status: str
    max_source_bundle_uploads: int = 1
    max_dependency_bundle_uploads: int = 1
    upload_only_after_ssh_banner_readiness: bool = True
    verify_source_hash_before_dependency_upload: bool = True
    verify_dependency_hash_before_extract_or_install: bool = True
    stop_and_terminate_on_source_upload_failure: bool = True
    stop_and_terminate_on_dependency_upload_failure: bool = True
    upload_retry_allowed_without_future_operator_approval: bool = False
    package_install_allowed_after_dependency_failure: bool = False
    manifest_execution_allowed_before_bundle_verification: bool = False
    extra_file_transfers_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSourceDependencyUploadPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("upload policy must remain future-only")
        if self.max_source_bundle_uploads != 1 or self.max_dependency_bundle_uploads != 1:
            raise ValueError("upload policy must stay one-shot")
        if self.upload_retry_allowed_without_future_operator_approval:
            raise ValueError("upload retry requires a future operator-approved milestone")
        if self.package_install_allowed_after_dependency_failure:
            raise ValueError("cannot install packages after dependency upload failure")
        if self.manifest_execution_allowed_before_bundle_verification:
            raise ValueError("cannot run manifest before bundle verification")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_source_dependency_upload_policy_from_path(
    *,
    upload_readiness_gate: str | Path,
) -> LambdaSourceDependencyUploadPolicy:
    gate = load_lambda_upload_readiness_gate_policy(upload_readiness_gate)
    blockers: list[str] = []
    if gate.gate_policy_status != "policy_defined":
        blockers.append("upload_readiness_gate_not_defined")
    if not gate.ssh_banner_readiness_required:
        blockers.append("ssh_banner_readiness_not_required")
    if gate.upload_before_readiness_allowed:
        blockers.append("upload_before_readiness_allowed")
    return LambdaSourceDependencyUploadPolicy(
        upload_policy_status="policy_defined" if not blockers else "blocked",
        blockers=blockers,
        warnings=[
            "source hash verification must pass before dependency upload",
            "dependency hash verification must pass before local-only install",
        ],
    )


def load_lambda_source_dependency_upload_policy(
    path: str | Path,
) -> LambdaSourceDependencyUploadPolicy:
    return LambdaSourceDependencyUploadPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_source_dependency_upload_policy(
    path: str | Path,
    report: LambdaSourceDependencyUploadPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
