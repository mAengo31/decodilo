"""M090 next-step decision after M089R closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    load_lambda_scaffold_completion_final_decision,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    load_lambda_scientific_gap_assessment,
)

PostM089RecommendedPath = Literal[
    "pause_and_analyze_bounded_experiment",
    "plan_true_model_fragment_smoke",
    "plan_small_real_training_smoke",
    "plan_multi_learner_synthetic_experiment",
]


class LambdaPostM089NextStepDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
    decision_status: str
    recommended_path: PostM089RecommendedPath
    rationale: str
    no_automatic_live_authorization: bool = True
    no_new_scaffold_category_by_default: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_decision(self) -> LambdaPostM089NextStepDecision:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("post-M089 decision must not authorize launch or spend")
        if self.no_automatic_live_authorization is not True:
            raise ValueError("M090 cannot authorize another live run")
        if self.decision_status == "next_step_decided" and self.blockers:
            raise ValueError("decided next step cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_post_m089_next_step_decision_from_paths(
    *,
    scaffold_final_decision: str | Path,
    scientific_gap_assessment: str | Path,
) -> LambdaPostM089NextStepDecision:
    scaffold = load_lambda_scaffold_completion_final_decision(scaffold_final_decision)
    gaps = load_lambda_scientific_gap_assessment(scientific_gap_assessment)
    blockers: list[str] = []
    if scaffold.scaffold_final_status != "complete":
        blockers.append("scaffold_final_status_not_complete")
    if gaps.assessment_status != "scientific_gaps_assessed":
        blockers.append("scientific_gaps_not_assessed")
    recommended: PostM089RecommendedPath = "pause_and_analyze_bounded_experiment"
    rationale = (
        "M089R is the first complete bounded synthetic DiLoCo experiment, so the "
        "next step should pause and analyze the persisted bounded artifact before "
        "authorizing a new live scientific extension."
    )
    return LambdaPostM089NextStepDecision(
        decision_status="next_step_decided" if not blockers else "blocked",
        recommended_path=recommended,
        rationale=rationale,
        blockers=blockers,
        warnings=[
            "M090 intentionally creates no future live authorization",
            "candidate future branches are true model fragments, small real training, "
            "or multi-learner synthetic scale-up after analysis",
        ],
    )


def load_lambda_post_m089_next_step_decision(
    path: str | Path,
) -> LambdaPostM089NextStepDecision:
    return LambdaPostM089NextStepDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_post_m089_next_step_decision(
    path: str | Path,
    report: LambdaPostM089NextStepDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
