"""M091 scientific claim boundaries for M089R."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_audit import (
    load_lambda_bounded_diloco_experiment_artifact_audit,
)
from decodilo.lambda_cloud.bounded_experiment_evidence_interpretation import (
    load_lambda_bounded_experiment_evidence_interpretation,
)


class LambdaScientificClaimBoundaries(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    boundary_status: str
    safe_claims: list[str] = Field(default_factory=list)
    unsafe_claims: list[str] = Field(default_factory=list)
    required_qualifiers: list[str] = Field(default_factory=list)
    overclaim_guardrails: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_boundaries(self) -> LambdaScientificClaimBoundaries:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("scientific claim boundaries must remain offline")
        if self.boundary_status == "claim_boundaries_defined" and self.blockers:
            raise ValueError("defined claim boundaries cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_scientific_claim_boundaries_from_paths(
    *,
    evidence_interpretation: str | Path,
    artifact_audit: str | Path,
) -> LambdaScientificClaimBoundaries:
    interpretation = load_lambda_bounded_experiment_evidence_interpretation(
        evidence_interpretation
    )
    audit = load_lambda_bounded_diloco_experiment_artifact_audit(artifact_audit)
    blockers: list[str] = []
    if interpretation.interpretation_status != "evidence_interpreted":
        blockers.append("evidence_not_interpreted")
    if not audit.artifact_audit_passed:
        blockers.append("artifact_audit_not_passed")
    safe_claims = [
        "first_remote_bounded_synthetic_diloco_experiment_completed",
        "synthetic_single_learner_single_sync_round_protocol_passed",
        "tiny_deterministic_adamw_inner_nesterov_outer_checks_passed",
        "pseudo_gradient_optimizer_state_and_reference_checks_passed",
        "synthetic_vector_fragment_checks_passed",
        "remote_artifact_capture_secret_scan_and_safe_parse_passed",
    ]
    unsafe_claims = [
        "real_model_training_completed",
        "paper_scale_diloco_validated",
        "true_model_or_layer_fragmentation_validated",
        "communication_computation_overlap_validated",
        "quantized_communication_validated",
        "multi_learner_or_multi_node_scaling_validated",
        "dataset_or_model_pipeline_validated",
    ]
    return LambdaScientificClaimBoundaries(
        boundary_status="claim_boundaries_defined" if not blockers else "blocked",
        safe_claims=safe_claims,
        unsafe_claims=unsafe_claims,
        required_qualifiers=[
            "bounded",
            "synthetic",
            "tiny deterministic state",
            "not real training",
            "not paper-scale DiLoCo",
            "synthetic vector fragments only",
        ],
        overclaim_guardrails=[
            "Do not drop the words bounded or synthetic from M089R claims.",
            "Do not claim true model fragments until tensor/model fragment paths run.",
            "Do not claim training until a real training loop runs.",
            "Do not claim overlap or quantization until those mechanisms run.",
        ],
        blockers=blockers,
        warnings=["claim boundaries do not authorize future live execution"],
    )


def load_lambda_scientific_claim_boundaries(
    path: str | Path,
) -> LambdaScientificClaimBoundaries:
    return LambdaScientificClaimBoundaries.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_scientific_claim_boundaries(
    path: str | Path,
    report: LambdaScientificClaimBoundaries,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
