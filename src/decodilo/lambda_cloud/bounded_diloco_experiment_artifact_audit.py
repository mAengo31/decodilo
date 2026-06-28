"""Offline audit of the M089R bounded synthetic DiLoCo experiment artifact."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_success_record import (
    M089R_BOUNDED_DILOCO_ARTIFACT_BYTES,
    M089R_BOUNDED_DILOCO_ARTIFACT_PATH,
    M089R_BOUNDED_DILOCO_ARTIFACT_SHA256,
    load_lambda_bounded_diloco_experiment_success_record,
)


class LambdaBoundedDilocoExperimentArtifactAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
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
    bounded_diloco_experiment_status: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    learners_observed: int | None = None
    sync_rounds_completed: int | None = None
    fragments_observed: int | None = None
    max_abs_error: float | None = None
    full_diloco_training_claimed: bool | None = None
    real_model_training_claimed: bool | None = None
    true_model_fragment_claimed: bool | None = None
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
    def _validate_audit(self) -> LambdaBoundedDilocoExperimentArtifactAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("bounded experiment artifact audit must remain offline")
        if self.artifact_audit_passed and self.blockers:
            raise ValueError("passing artifact audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_diloco_experiment_artifact_audit_from_paths(
    *,
    workdir: str | Path,
    success_record: str | Path,
) -> LambdaBoundedDilocoExperimentArtifactAudit:
    record = load_lambda_bounded_diloco_experiment_success_record(success_record)
    report_path = Path(workdir) / "report.json"
    evidence_path = Path(workdir) / "remote-vslice-evidence.json"
    blockers: list[str] = []
    artifact_type_expected = str(record.artifact_path or "").endswith(".json")
    if record.artifact_path != M089R_BOUNDED_DILOCO_ARTIFACT_PATH:
        blockers.append("unexpected_artifact_path")
    if record.artifact_bytes != M089R_BOUNDED_DILOCO_ARTIFACT_BYTES:
        blockers.append("unexpected_artifact_size")
    if record.artifact_sha256 != M089R_BOUNDED_DILOCO_ARTIFACT_SHA256:
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
    if record.bounded_diloco_experiment_status != "passed":
        blockers.append("bounded_diloco_experiment_status_not_passed")
    if record.optimization_fidelity != "bounded_synthetic_diloco_experiment":
        blockers.append("bounded_optimization_fidelity_not_verified")
    if record.inner_optimizer_semantics != "adamw":
        blockers.append("inner_optimizer_semantics_not_adamw")
    if record.outer_optimizer_semantics != "nesterov":
        blockers.append("outer_optimizer_semantics_not_nesterov")
    if record.parameter_fragment_semantics != "synthetic_vector_fragments":
        blockers.append("parameter_fragment_semantics_not_synthetic_vector_fragments")
    if record.learners_observed != 1:
        blockers.append("learners_observed_not_one")
    if record.sync_rounds_completed != 1:
        blockers.append("sync_rounds_completed_not_one")
    if record.fragments_observed != 2:
        blockers.append("fragments_observed_not_two")
    if record.max_abs_error != 0.0:
        blockers.append("max_abs_error_nonzero")
    if record.full_diloco_training_claimed is not False:
        blockers.append("full_diloco_training_claimed")
    if record.real_model_training_claimed is not False:
        blockers.append("real_model_training_claimed")
    if record.true_model_fragment_claimed is not False:
        blockers.append("true_model_fragment_claimed")
    if record.overlap_semantics != "not_exercised":
        blockers.append("overlap_semantics_overclaimed")
    if record.quantization_semantics != "not_exercised":
        blockers.append("quantization_semantics_overclaimed")
    sources = [str(path) for path in [report_path, evidence_path] if path.exists()]
    return LambdaBoundedDilocoExperimentArtifactAudit(
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
        bounded_diloco_experiment_status=record.bounded_diloco_experiment_status,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        learners_observed=record.learners_observed,
        sync_rounds_completed=record.sync_rounds_completed,
        fragments_observed=record.fragments_observed,
        max_abs_error=record.max_abs_error,
        full_diloco_training_claimed=record.full_diloco_training_claimed,
        real_model_training_claimed=record.real_model_training_claimed,
        true_model_fragment_claimed=record.true_model_fragment_claimed,
        overlap_semantics=record.overlap_semantics,
        quantization_semantics=record.quantization_semantics,
        no_raw_secrets=record.artifact_secret_scan_passed,
        evidence_sources=sources,
        blockers=blockers,
        warnings=[
            "artifact audit uses persisted M089R evidence only",
            "audit confirms bounded synthetic DiLoCo semantics without claiming "
            "real training, true model fragments, overlap, or quantization",
        ],
    )


def load_lambda_bounded_diloco_experiment_artifact_audit(
    path: str | Path,
) -> LambdaBoundedDilocoExperimentArtifactAudit:
    return LambdaBoundedDilocoExperimentArtifactAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_diloco_experiment_artifact_audit(
    path: str | Path,
    report: LambdaBoundedDilocoExperimentArtifactAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
