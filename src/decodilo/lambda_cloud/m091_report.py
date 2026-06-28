"""Aggregate M091 scientific decision package report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_experiment_evidence_interpretation import (
    load_lambda_bounded_experiment_evidence_interpretation,
)
from decodilo.lambda_cloud.bounded_experiment_result_summary import (
    load_lambda_bounded_experiment_result_summary,
)
from decodilo.lambda_cloud.post_m090_next_branch_decision import (
    load_lambda_post_m090_next_branch_decision,
)
from decodilo.lambda_cloud.remaining_gap_prioritization import (
    load_lambda_remaining_gap_prioritization,
)
from decodilo.lambda_cloud.scientific_claim_boundaries import (
    load_lambda_scientific_claim_boundaries,
)


class LambdaM091Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    report_passed: bool
    scaffold_completion_status: str
    bounded_experiment_interpretation_status: str
    safe_claims: list[str] = Field(default_factory=list)
    unsafe_claims: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    recommended_next_branch: str
    another_scaffold_run_justified: bool
    no_live_authorization: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM091Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M091 report must remain offline")
        if self.no_live_authorization is not True:
            raise ValueError("M091 report cannot authorize live execution")
        if self.report_passed and self.blockers:
            raise ValueError("passing M091 report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m091_report_from_paths(
    *,
    result_summary: str | Path,
    evidence_interpretation: str | Path,
    claim_boundaries: str | Path,
    gap_prioritization: str | Path,
    next_branch_decision: str | Path,
) -> LambdaM091Report:
    summary = load_lambda_bounded_experiment_result_summary(result_summary)
    interpretation = load_lambda_bounded_experiment_evidence_interpretation(
        evidence_interpretation
    )
    boundaries = load_lambda_scientific_claim_boundaries(claim_boundaries)
    prioritization = load_lambda_remaining_gap_prioritization(gap_prioritization)
    decision = load_lambda_post_m090_next_branch_decision(next_branch_decision)
    blockers: list[str] = []
    if summary.summary_status != "bounded_synthetic_diloco_experiment_summarized":
        blockers.append("result_summary_not_passed")
    if interpretation.interpretation_status != "evidence_interpreted":
        blockers.append("evidence_interpretation_not_passed")
    if boundaries.boundary_status != "claim_boundaries_defined":
        blockers.append("claim_boundaries_not_defined")
    if prioritization.prioritization_status != "remaining_gaps_prioritized":
        blockers.append("remaining_gaps_not_prioritized")
    if decision.decision_status != "next_branch_selected":
        blockers.append("next_branch_not_selected")
    if decision.no_live_authorization is not True:
        blockers.append("live_authorization_created")
    return LambdaM091Report(
        report_passed=not blockers,
        scaffold_completion_status=(
            "complete" if interpretation.scaffold_phase_complete else "incomplete"
        ),
        bounded_experiment_interpretation_status=interpretation.interpretation_status,
        safe_claims=boundaries.safe_claims,
        unsafe_claims=boundaries.unsafe_claims,
        remaining_gaps=prioritization.remaining_gaps,
        recommended_next_branch=decision.recommended_branch,
        another_scaffold_run_justified=(
            interpretation.another_scaffold_run_justified
        ),
        no_live_authorization=decision.no_live_authorization,
        historical_billable_action_performed=(
            summary.historical_billable_action_performed
        ),
        blockers=blockers,
        warnings=[
            "M091 is analysis-only and performs no billable action",
            "next branch selection is planning guidance only",
        ],
    )


def load_lambda_m091_report(path: str | Path) -> LambdaM091Report:
    return LambdaM091Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m091_report(path: str | Path, report: LambdaM091Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
