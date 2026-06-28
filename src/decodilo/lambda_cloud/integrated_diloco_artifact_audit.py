"""Offline audit of the M085R integrated synthetic DiLoCo artifact."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_success_record import (
    M085R_INTEGRATED_ARTIFACT_BYTES,
    M085R_INTEGRATED_ARTIFACT_PATH,
    M085R_INTEGRATED_ARTIFACT_SHA256,
    load_lambda_integrated_diloco_success_record,
)


class LambdaIntegratedDilocoArtifactAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086"
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
    integrated_diloco_smoke_status: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    protocol_optimizer_link_check_passed: bool | None = None
    pseudo_gradient_check_passed: bool | None = None
    inner_adamw_check_passed: bool | None = None
    outer_nesterov_check_passed: bool | None = None
    optimizer_state_roundtrip_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    reference_value_check_passed: bool | None = None
    max_abs_error: float | None = None
    no_raw_secrets: bool
    evidence_sources: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_audit(self) -> LambdaIntegratedDilocoArtifactAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("integrated DiLoCo artifact audit must remain offline")
        if self.artifact_audit_passed and self.blockers:
            raise ValueError("passing artifact audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_integrated_diloco_artifact_audit_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaIntegratedDilocoArtifactAudit:
    record = load_lambda_integrated_diloco_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    evidence_path = Path(workdir) / "remote-vslice-evidence.json"
    blockers: list[str] = []
    artifact_type_expected = str(record.artifact_path or "").endswith(".json")
    if record.artifact_path != M085R_INTEGRATED_ARTIFACT_PATH:
        blockers.append("unexpected_artifact_path")
    if record.artifact_bytes != M085R_INTEGRATED_ARTIFACT_BYTES:
        blockers.append("unexpected_artifact_size")
    if record.artifact_sha256 != M085R_INTEGRATED_ARTIFACT_SHA256:
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
    if record.integrated_diloco_smoke_status != "passed":
        blockers.append("integrated_diloco_smoke_status_not_passed")
    if record.optimization_fidelity != "integrated_optimizer_protocol_smoke":
        blockers.append("integrated_fidelity_not_verified")
    if record.inner_optimizer_semantics != "adamw":
        blockers.append("inner_optimizer_semantics_unexpected")
    if record.outer_optimizer_semantics != "nesterov":
        blockers.append("outer_optimizer_semantics_unexpected")
    if record.parameter_fragment_semantics != "not_exercised":
        blockers.append("parameter_fragment_semantics_unexpected")
    for key, value in {
        "protocol_optimizer_link": record.protocol_optimizer_link_check_passed,
        "pseudo_gradient": record.pseudo_gradient_check_passed,
        "inner_adamw": record.inner_adamw_check_passed,
        "outer_nesterov": record.outer_nesterov_check_passed,
        "optimizer_state_roundtrip": record.optimizer_state_roundtrip_check_passed,
        "replay_or_metric": record.replay_or_metric_check_passed,
        "reference_value": record.reference_value_check_passed,
    }.items():
        if value is not True:
            blockers.append(f"{key}_check_not_passed")
    if record.max_abs_error != 0.0:
        blockers.append("max_abs_error_nonzero")
    sources = [str(path) for path in [report_path, evidence_path] if path.exists()]
    return LambdaIntegratedDilocoArtifactAudit(
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
        integrated_diloco_smoke_status=record.integrated_diloco_smoke_status,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        protocol_optimizer_link_check_passed=(
            record.protocol_optimizer_link_check_passed
        ),
        pseudo_gradient_check_passed=record.pseudo_gradient_check_passed,
        inner_adamw_check_passed=record.inner_adamw_check_passed,
        outer_nesterov_check_passed=record.outer_nesterov_check_passed,
        optimizer_state_roundtrip_check_passed=(
            record.optimizer_state_roundtrip_check_passed
        ),
        replay_or_metric_check_passed=record.replay_or_metric_check_passed,
        reference_value_check_passed=record.reference_value_check_passed,
        max_abs_error=record.max_abs_error,
        no_raw_secrets=record.artifact_secret_scan_passed,
        evidence_sources=sources,
        blockers=blockers,
        warnings=[
            "artifact audit uses persisted M085R evidence only",
            "audit confirms integrated smoke semantics without claiming "
            "parameter-fragment synchronization",
        ],
    )


def load_lambda_integrated_diloco_artifact_audit(
    path: str | Path,
) -> LambdaIntegratedDilocoArtifactAudit:
    return LambdaIntegratedDilocoArtifactAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_integrated_diloco_artifact_audit(
    path: str | Path,
    report: LambdaIntegratedDilocoArtifactAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
