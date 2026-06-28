"""Offline audit of the M081R2 DiLoCo-shaped synthetic artifact."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_success_record import (
    M081R2_DILOCO_ARTIFACT_BYTES,
    M081R2_DILOCO_ARTIFACT_PATH,
    M081R2_DILOCO_ARTIFACT_SHA256,
    load_lambda_diloco_synthetic_success_record,
)


class LambdaDilocoSyntheticArtifactAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082"
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
    diloco_smoke_status: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    diloco_shape_check_passed: bool | None = None
    learner_syncer_exchange_check_passed: bool | None = None
    update_or_commit_check_passed: bool | None = None
    replay_or_metric_check_passed: bool | None = None
    no_raw_secrets: bool
    evidence_sources: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_audit(self) -> LambdaDilocoSyntheticArtifactAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo synthetic artifact audit must remain offline")
        if self.artifact_audit_passed and self.blockers:
            raise ValueError("passing artifact audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_synthetic_artifact_audit_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaDilocoSyntheticArtifactAudit:
    record = load_lambda_diloco_synthetic_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    evidence_path = Path(workdir) / "remote-vslice-evidence.json"
    blockers: list[str] = []
    artifact_type_expected = str(record.artifact_path or "").endswith(".json")
    if record.artifact_path != M081R2_DILOCO_ARTIFACT_PATH:
        blockers.append("unexpected_artifact_path")
    if record.artifact_bytes != M081R2_DILOCO_ARTIFACT_BYTES:
        blockers.append("unexpected_artifact_size")
    if record.artifact_sha256 != M081R2_DILOCO_ARTIFACT_SHA256:
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
    if record.diloco_smoke_status != "passed":
        blockers.append("diloco_smoke_status_not_passed")
    if record.optimization_fidelity != "diloco_shaped_protocol_only":
        blockers.append("optimization_fidelity_overclaimed_or_missing")
    if record.inner_optimizer_semantics != "synthetic_placeholder":
        blockers.append("inner_optimizer_semantics_unexpected")
    if record.outer_optimizer_semantics != "token_weighted_merge":
        blockers.append("outer_optimizer_semantics_unexpected")
    if record.parameter_fragment_semantics != "not_exercised":
        blockers.append("parameter_fragment_semantics_unexpected")
    if record.diloco_shape_check_passed is not True:
        blockers.append("diloco_shape_check_not_passed")
    if record.learner_syncer_exchange_check_passed is not True:
        blockers.append("learner_syncer_exchange_check_not_passed")
    if record.update_or_commit_check_passed is not True:
        blockers.append("update_or_commit_check_not_passed")
    if record.replay_or_metric_check_passed is not True:
        blockers.append("replay_or_metric_check_not_passed")
    sources = [str(path) for path in [report_path, evidence_path] if path.exists()]
    return LambdaDilocoSyntheticArtifactAudit(
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
        diloco_smoke_status=record.diloco_smoke_status,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        diloco_shape_check_passed=record.diloco_shape_check_passed,
        learner_syncer_exchange_check_passed=record.learner_syncer_exchange_check_passed,
        update_or_commit_check_passed=record.update_or_commit_check_passed,
        replay_or_metric_check_passed=record.replay_or_metric_check_passed,
        no_raw_secrets=record.artifact_secret_scan_passed,
        evidence_sources=sources,
        blockers=blockers,
        warnings=[
            "artifact audit uses persisted M081R2 evidence only",
            "audit confirms DiLoCo optimizer fidelity is not overclaimed",
        ],
    )


def load_lambda_diloco_synthetic_artifact_audit(
    path: str | Path,
) -> LambdaDilocoSyntheticArtifactAudit:
    return LambdaDilocoSyntheticArtifactAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_artifact_audit(
    path: str | Path,
    report: LambdaDilocoSyntheticArtifactAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
