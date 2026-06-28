"""M091 interpretation of the bounded synthetic DiLoCo evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_closeout import (
    load_lambda_bounded_diloco_experiment_closeout,
)
from decodilo.lambda_cloud.bounded_experiment_result_summary import (
    load_lambda_bounded_experiment_result_summary,
)
from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    load_lambda_scaffold_completion_final_decision,
)


class LambdaBoundedExperimentEvidenceInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    interpretation_status: str
    scaffold_phase_complete: bool
    another_scaffold_run_justified: bool
    bounded_experiment_closed: bool
    evidence_supports_safe_claims: bool
    evidence_rejects_unsafe_claims: bool
    what_m089r_proves: list[str] = Field(default_factory=list)
    what_m089r_does_not_prove: list[str] = Field(default_factory=list)
    interpretation: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_interpretation(self) -> LambdaBoundedExperimentEvidenceInterpretation:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M091 evidence interpretation must remain offline")
        if self.interpretation_status == "evidence_interpreted" and self.blockers:
            raise ValueError("passing evidence interpretation cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_experiment_evidence_interpretation_from_paths(
    *,
    result_summary: str | Path,
    closeout: str | Path,
    scaffold_final_decision: str | Path,
) -> LambdaBoundedExperimentEvidenceInterpretation:
    summary = load_lambda_bounded_experiment_result_summary(result_summary)
    closeout_report = load_lambda_bounded_diloco_experiment_closeout(closeout)
    scaffold = load_lambda_scaffold_completion_final_decision(
        scaffold_final_decision
    )
    blockers: list[str] = []
    if summary.summary_status != "bounded_synthetic_diloco_experiment_summarized":
        blockers.append("result_summary_not_passed")
    if not closeout_report.closeout_succeeded:
        blockers.append("bounded_closeout_not_succeeded")
    if scaffold.scaffold_final_status != "complete":
        blockers.append("scaffold_final_status_not_complete")
    another_scaffold = False
    interpretation = (
        "M089R supports a safe claim that the remote bounded synthetic DiLoCo "
        "experiment path works end to end over tiny deterministic synthetic state. "
        "It does not support claims about real model training, paper-scale DiLoCo, "
        "true model fragments, overlap, quantization, or multi-node scale."
    )
    return LambdaBoundedExperimentEvidenceInterpretation(
        interpretation_status="evidence_interpreted" if not blockers else "blocked",
        scaffold_phase_complete=scaffold.scaffold_final_status == "complete",
        another_scaffold_run_justified=another_scaffold,
        bounded_experiment_closed=closeout_report.closeout_succeeded,
        evidence_supports_safe_claims=not blockers,
        evidence_rejects_unsafe_claims=not blockers,
        what_m089r_proves=summary.m089r_proves,
        what_m089r_does_not_prove=summary.m089r_does_not_prove,
        interpretation=interpretation,
        blockers=blockers,
        warnings=[
            "no additional scaffold run is justified absent a concrete failure",
        ],
    )


def load_lambda_bounded_experiment_evidence_interpretation(
    path: str | Path,
) -> LambdaBoundedExperimentEvidenceInterpretation:
    return LambdaBoundedExperimentEvidenceInterpretation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_experiment_evidence_interpretation(
    path: str | Path,
    report: LambdaBoundedExperimentEvidenceInterpretation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
