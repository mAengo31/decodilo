"""Offline audit of the M087R parameter-fragment smoke artifact."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.parameter_fragment_success_record import (
    M087R_PARAMETER_FRAGMENT_ARTIFACT_BYTES,
    M087R_PARAMETER_FRAGMENT_ARTIFACT_PATH,
    M087R_PARAMETER_FRAGMENT_ARTIFACT_SHA256,
    load_lambda_parameter_fragment_success_record,
)


class LambdaParameterFragmentArtifactAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    artifact_audit_passed: bool
    artifact_path: str | None = None
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    artifact_type: str | None = None
    artifact_type_expected: bool
    artifact_bounded: bool
    secret_scan_passed: bool
    safe_json_body_persisted: bool
    parsed_summary_persisted: bool
    parameter_fragment_smoke_status: str | None = None
    parameter_fragment_semantics: str | None = None
    fragment_count: int | None = None
    fragment_update_check_passed: bool | None = None
    fragment_merge_check_passed: bool | None = None
    fragment_reconstruction_check_passed: bool | None = None
    fragment_schedule_check_passed: bool | None = None
    fragment_state_roundtrip_check_passed: bool | None = None
    per_fragment_reference_check_passed: bool | None = None
    global_reference_check_passed: bool | None = None
    max_abs_error: float | None = None
    overlap_semantics: str | None = None
    quantization_semantics: str | None = None
    no_raw_secrets: bool
    evidence_sources: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_audit(self) -> LambdaParameterFragmentArtifactAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("parameter-fragment artifact audit must remain offline")
        if self.artifact_audit_passed and self.blockers:
            raise ValueError("passing artifact audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_parameter_fragment_artifact_audit_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaParameterFragmentArtifactAudit:
    record = load_lambda_parameter_fragment_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    evidence_path = Path(workdir) / "remote-vslice-evidence.json"
    blockers: list[str] = []
    artifact_type_expected = str(record.artifact_path or "").endswith(".json")
    if record.artifact_path != M087R_PARAMETER_FRAGMENT_ARTIFACT_PATH:
        blockers.append("unexpected_artifact_path")
    if record.artifact_bytes != M087R_PARAMETER_FRAGMENT_ARTIFACT_BYTES:
        blockers.append("unexpected_artifact_size")
    if record.artifact_sha256 != M087R_PARAMETER_FRAGMENT_ARTIFACT_SHA256:
        blockers.append("unexpected_artifact_sha256")
    if not artifact_type_expected:
        blockers.append("unexpected_artifact_type")
    if not record.artifact_bounded:
        blockers.append("artifact_not_bounded")
    if not record.artifact_secret_scan_passed:
        blockers.append("artifact_secret_scan_failed")
    if not record.safe_json_body_persisted:
        blockers.append("safe_json_body_not_persisted")
    if not record.parsed_summary_persisted:
        blockers.append("parsed_summary_not_persisted")
    if record.parameter_fragment_smoke_status != "passed":
        blockers.append("parameter_fragment_smoke_status_not_passed")
    if record.parameter_fragment_semantics != "synthetic_vector_fragments":
        blockers.append("fragment_semantics_not_verified")
    if record.fragment_count != 2:
        blockers.append("fragment_count_not_two")
    for key, value in {
        "fragment_update": record.fragment_update_check_passed,
        "fragment_merge": record.fragment_merge_check_passed,
        "fragment_reconstruction": record.fragment_reconstruction_check_passed,
        "fragment_schedule": record.fragment_schedule_check_passed,
        "fragment_state_roundtrip": record.fragment_state_roundtrip_check_passed,
        "per_fragment_reference": record.per_fragment_reference_check_passed,
        "global_reference": record.global_reference_check_passed,
    }.items():
        if value is not True:
            blockers.append(f"{key}_check_not_passed")
    if record.max_abs_error != 0.0:
        blockers.append("max_abs_error_nonzero")
    if record.overlap_semantics != "not_exercised":
        blockers.append("overlap_semantics_overclaimed")
    if record.quantization_semantics != "not_exercised":
        blockers.append("quantization_semantics_overclaimed")
    sources = [str(path) for path in [report_path, evidence_path] if path.exists()]
    return LambdaParameterFragmentArtifactAudit(
        artifact_audit_passed=not blockers,
        artifact_path=record.artifact_path,
        artifact_bytes=record.artifact_bytes,
        artifact_sha256=record.artifact_sha256,
        artifact_type="JSON" if artifact_type_expected else None,
        artifact_type_expected=artifact_type_expected,
        artifact_bounded=record.artifact_bounded,
        secret_scan_passed=record.artifact_secret_scan_passed,
        safe_json_body_persisted=record.safe_json_body_persisted,
        parsed_summary_persisted=record.parsed_summary_persisted,
        parameter_fragment_smoke_status=record.parameter_fragment_smoke_status,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        fragment_count=record.fragment_count,
        fragment_update_check_passed=record.fragment_update_check_passed,
        fragment_merge_check_passed=record.fragment_merge_check_passed,
        fragment_reconstruction_check_passed=record.fragment_reconstruction_check_passed,
        fragment_schedule_check_passed=record.fragment_schedule_check_passed,
        fragment_state_roundtrip_check_passed=(
            record.fragment_state_roundtrip_check_passed
        ),
        per_fragment_reference_check_passed=record.per_fragment_reference_check_passed,
        global_reference_check_passed=record.global_reference_check_passed,
        max_abs_error=record.max_abs_error,
        overlap_semantics=record.overlap_semantics,
        quantization_semantics=record.quantization_semantics,
        no_raw_secrets=record.artifact_secret_scan_passed,
        evidence_sources=sources,
        blockers=blockers,
        warnings=[
            "artifact audit uses persisted M087R evidence only",
            "audit confirms synthetic vector-fragment semantics without claiming "
            "true model fragments, overlap, or quantization",
        ],
    )


def load_lambda_parameter_fragment_artifact_audit(
    path: str | Path,
) -> LambdaParameterFragmentArtifactAudit:
    return LambdaParameterFragmentArtifactAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_parameter_fragment_artifact_audit(
    path: str | Path,
    report: LambdaParameterFragmentArtifactAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
