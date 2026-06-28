"""M090 scientific gap assessment after bounded synthetic DiLoCo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_audit import (
    load_lambda_bounded_diloco_experiment_artifact_audit,
)

LambdaScientificGapAssessmentStatus = Literal[
    "scientific_gaps_assessed",
    "blocked_bounded_artifact_audit_failed",
]


class LambdaScientificGapAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
    assessment_status: LambdaScientificGapAssessmentStatus
    bounded_experiment_artifact_audit_passed: bool
    real_model_training_done: bool = False
    real_dataset_model_pipeline_done: bool = False
    true_model_layer_parameter_fragments_done: bool = False
    communication_computation_overlap_done: bool = False
    quantized_communication_done: bool = False
    multi_learner_or_multi_node_cloud_orchestration_done: bool = False
    larger_scale_experiment_metrics_done: bool = False
    paper_scale_diloco_comparison_done: bool = False
    recommended_extension: str = "pause_and_analyze_bounded_experiment"
    remaining_gaps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_assessment(self) -> LambdaScientificGapAssessment:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("scientific gap assessment must remain offline")
        if self.assessment_status == "scientific_gaps_assessed" and self.blockers:
            raise ValueError("passing scientific gap assessment cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_scientific_gap_assessment_from_path(
    *,
    bounded_artifact_audit: str | Path,
) -> LambdaScientificGapAssessment:
    audit = load_lambda_bounded_diloco_experiment_artifact_audit(
        bounded_artifact_audit
    )
    blockers: list[str] = []
    if not audit.artifact_audit_passed:
        blockers.append("bounded_artifact_audit_not_passed")
    remaining_gaps = [
        "real_model_training_not_done",
        "real_dataset_model_pipeline_not_done",
        "true_model_layer_parameter_fragments_not_done",
        "communication_computation_overlap_not_done",
        "quantized_communication_not_done",
        "multi_learner_or_multi_node_cloud_orchestration_not_done",
        "larger_scale_experiment_metrics_not_done",
        "paper_scale_diloco_comparison_not_done",
    ]
    return LambdaScientificGapAssessment(
        assessment_status=(
            "scientific_gaps_assessed"
            if not blockers
            else "blocked_bounded_artifact_audit_failed"
        ),
        bounded_experiment_artifact_audit_passed=audit.artifact_audit_passed,
        remaining_gaps=remaining_gaps,
        blockers=blockers,
        warnings=[
            "M089R establishes a bounded synthetic baseline, not real training",
            "next work should be chosen from explicit scientific gaps, not by "
            "adding another scaffold category",
        ],
    )


def load_lambda_scientific_gap_assessment(
    path: str | Path,
) -> LambdaScientificGapAssessment:
    return LambdaScientificGapAssessment.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_scientific_gap_assessment(
    path: str | Path,
    report: LambdaScientificGapAssessment,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
