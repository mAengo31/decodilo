"""Offline audit of the M071R generated remote artifact metadata."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_success_record import (
    M071R_OUTPUT_ARTIFACT_BYTES,
    M071R_OUTPUT_ARTIFACT_PATH,
    M071R_OUTPUT_ARTIFACT_SHA256,
    load_lambda_first_experiment_success_record,
)


class LambdaRemoteArtifactAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072"
    artifact_audit_passed: bool
    artifact_path: str | None = None
    artifact_size_bytes: int | None = None
    artifact_sha256: str | None = None
    artifact_type_expected: bool
    artifact_bounded: bool
    secret_scan_passed: bool
    no_raw_secrets: bool
    evidence_sources: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_audit(self) -> LambdaRemoteArtifactAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("remote artifact audit must remain offline and disabled")
        if self.artifact_audit_passed and self.blockers:
            raise ValueError("passing artifact audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_artifact_audit_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaRemoteArtifactAudit:
    record = load_lambda_first_experiment_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    evidence_path = Path(workdir) / "remote-vslice-evidence.json"
    blockers: list[str] = []
    artifact_type_expected = str(record.artifact_path or "").endswith(".json")
    if record.artifact_path != M071R_OUTPUT_ARTIFACT_PATH:
        blockers.append("unexpected_artifact_path")
    if record.artifact_bytes != M071R_OUTPUT_ARTIFACT_BYTES:
        blockers.append("unexpected_artifact_size")
    if record.artifact_sha256 != M071R_OUTPUT_ARTIFACT_SHA256:
        blockers.append("unexpected_artifact_sha256")
    if not artifact_type_expected:
        blockers.append("unexpected_artifact_type")
    if not record.artifact_bounded:
        blockers.append("artifact_not_bounded")
    if not record.artifact_secret_scan_passed:
        blockers.append("artifact_secret_scan_failed")
    if not record.ci_profile_report_artifact_created:
        blockers.append("artifact_not_created")
    sources = [str(path) for path in [report_path, evidence_path] if path.exists()]
    return LambdaRemoteArtifactAudit(
        artifact_audit_passed=not blockers,
        artifact_path=record.artifact_path,
        artifact_size_bytes=record.artifact_bytes,
        artifact_sha256=record.artifact_sha256,
        artifact_type_expected=artifact_type_expected,
        artifact_bounded=record.artifact_bounded,
        secret_scan_passed=record.artifact_secret_scan_passed,
        no_raw_secrets=record.artifact_secret_scan_passed,
        evidence_sources=sources,
        blockers=blockers,
        warnings=["artifact audit uses captured metadata only; no remote read is performed"],
    )


def load_lambda_remote_artifact_audit(path: str | Path) -> LambdaRemoteArtifactAudit:
    return LambdaRemoteArtifactAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_artifact_audit(
    path: str | Path,
    report: LambdaRemoteArtifactAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
