"""M091 bounded synthetic DiLoCo result summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_audit import (
    load_lambda_bounded_diloco_experiment_artifact_audit,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_success_record import (
    load_lambda_bounded_diloco_experiment_success_record,
)
from decodilo.lambda_cloud.m090_report import load_lambda_m090_report

BoundedExperimentResultSummaryStatus = Literal[
    "bounded_synthetic_diloco_experiment_summarized",
    "blocked_m090_not_passed",
]


class LambdaBoundedExperimentResultSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    summary_status: BoundedExperimentResultSummaryStatus
    bounded_experiment_success: bool
    m090_report_passed: bool
    artifact_audit_passed: bool
    artifact_sha256: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    learners_observed: int | None = None
    sync_rounds_completed: int | None = None
    fragments_observed: int | None = None
    max_abs_error: float | None = None
    m089r_proves: list[str] = Field(default_factory=list)
    m089r_does_not_prove: list[str] = Field(default_factory=list)
    no_real_training: bool
    no_true_model_fragment_claim: bool
    no_overlap_claim: bool
    no_quantization_claim: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_summary(self) -> LambdaBoundedExperimentResultSummary:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M091 result summary must remain offline")
        if self.summary_status.endswith("summarized") and self.blockers:
            raise ValueError("passing result summary cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_experiment_result_summary_from_paths(
    *,
    success_record: str | Path,
    artifact_audit: str | Path,
    m090_report: str | Path,
) -> LambdaBoundedExperimentResultSummary:
    record = load_lambda_bounded_diloco_experiment_success_record(success_record)
    audit = load_lambda_bounded_diloco_experiment_artifact_audit(artifact_audit)
    m090 = load_lambda_m090_report(m090_report)
    blockers: list[str] = []
    if (
        record.success_status
        != "remote_bounded_synthetic_diloco_experiment_success"
    ):
        blockers.append("m089r_success_record_not_success")
    if not audit.artifact_audit_passed:
        blockers.append("bounded_artifact_audit_not_passed")
    if not m090.report_passed:
        blockers.append("m090_report_not_passed")
    proves = [
        "remote_bounded_synthetic_diloco_experiment_completed",
        "remote_lifecycle_upload_install_command_artifact_teardown_path_passed",
        "single_learner_single_sync_round_synthetic_protocol_passed",
        "adamw_inner_and_nesterov_outer_optimizer_semantics_passed",
        "pseudo_gradient_and_optimizer_state_roundtrip_checks_passed",
        "synthetic_vector_fragment_update_merge_reconstruction_passed",
        "protocol_optimizer_fragment_link_checks_passed",
        "bounded_artifact_capture_and_safe_parse_passed",
    ]
    does_not_prove = [
        "real_model_training",
        "real_dataset_or_model_pipeline",
        "true_model_or_layer_parameter_fragments",
        "communication_computation_overlap",
        "quantized_communication",
        "multi_learner_or_multi_node_cloud_orchestration",
        "larger_scale_metrics_or_paper_scale_diloco_comparison",
    ]
    return LambdaBoundedExperimentResultSummary(
        summary_status=(
            "bounded_synthetic_diloco_experiment_summarized"
            if not blockers
            else "blocked_m090_not_passed"
        ),
        bounded_experiment_success=not blockers,
        m090_report_passed=m090.report_passed,
        artifact_audit_passed=audit.artifact_audit_passed,
        artifact_sha256=audit.artifact_sha256,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        learners_observed=record.learners_observed,
        sync_rounds_completed=record.sync_rounds_completed,
        fragments_observed=record.fragments_observed,
        max_abs_error=record.max_abs_error,
        m089r_proves=proves,
        m089r_does_not_prove=does_not_prove,
        no_real_training=record.no_real_training,
        no_true_model_fragment_claim=record.true_model_fragment_claimed is False,
        no_overlap_claim=record.overlap_semantics == "not_exercised",
        no_quantization_claim=record.quantization_semantics == "not_exercised",
        historical_billable_action_performed=(
            record.historical_billable_action_performed
        ),
        blockers=blockers,
        warnings=[
            "M091 result summary is analysis-only and creates no live authorization",
        ],
    )


def load_lambda_bounded_experiment_result_summary(
    path: str | Path,
) -> LambdaBoundedExperimentResultSummary:
    return LambdaBoundedExperimentResultSummary.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_experiment_result_summary(
    path: str | Path,
    report: LambdaBoundedExperimentResultSummary,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
