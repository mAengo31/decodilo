"""M091 prioritization of remaining scientific gaps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.scientific_claim_boundaries import (
    load_lambda_scientific_claim_boundaries,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    load_lambda_scientific_gap_assessment,
)

NextBranch = Literal[
    "pause_and_write_up_results",
    "plan_true_model_fragment_smoke",
    "plan_tiny_real_training_smoke",
    "plan_multi_learner_synthetic_experiment",
    "plan_parameter_fragment_real_tensor_upgrade",
]


class LambdaRemainingGapPrioritization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    prioritization_status: str
    recommended_branch: NextBranch
    branch_priorities: list[dict[str, str | int]] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    no_generic_smoke_category_recommended: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_prioritization(self) -> LambdaRemainingGapPrioritization:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("remaining-gap prioritization must remain offline")
        if self.prioritization_status == "remaining_gaps_prioritized" and self.blockers:
            raise ValueError("passing gap prioritization cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remaining_gap_prioritization_from_paths(
    *,
    scientific_gap_assessment: str | Path,
    claim_boundaries: str | Path,
) -> LambdaRemainingGapPrioritization:
    gaps = load_lambda_scientific_gap_assessment(scientific_gap_assessment)
    boundaries = load_lambda_scientific_claim_boundaries(claim_boundaries)
    blockers: list[str] = []
    if gaps.assessment_status != "scientific_gaps_assessed":
        blockers.append("scientific_gaps_not_assessed")
    if boundaries.boundary_status != "claim_boundaries_defined":
        blockers.append("claim_boundaries_not_defined")
    priorities: list[dict[str, str | int]] = [
        {
            "rank": 1,
            "branch": "plan_tiny_real_training_smoke",
            "goal_fit": "scientific_credibility_against_diloco",
            "rationale": (
                "M089R did not exercise a real training loop; a tiny "
                "generated-data training smoke is the smallest credibility upgrade."
            ),
        },
        {
            "rank": 2,
            "branch": "plan_parameter_fragment_real_tensor_upgrade",
            "goal_fit": "fragment_semantics_credibility",
            "rationale": (
                "M089R used synthetic vector fragments; tensor/model fragment "
                "semantics remain unproven."
            ),
        },
        {
            "rank": 3,
            "branch": "plan_multi_learner_synthetic_experiment",
            "goal_fit": "systems_scaling",
            "rationale": (
                "Useful after deciding to stress protocol scaling beyond the "
                "single-learner bounded baseline."
            ),
        },
        {
            "rank": 4,
            "branch": "pause_and_write_up_results",
            "goal_fit": "documentation_and_sanity",
            "rationale": (
                "Appropriate if the next objective is reporting rather than "
                "extending the evidence surface."
            ),
        },
    ]
    return LambdaRemainingGapPrioritization(
        prioritization_status=(
            "remaining_gaps_prioritized" if not blockers else "blocked"
        ),
        recommended_branch="plan_tiny_real_training_smoke",
        branch_priorities=priorities,
        remaining_gaps=gaps.remaining_gaps,
        blockers=blockers,
        warnings=[
            "prioritization is analysis-only and does not authorize a live run",
        ],
    )


def load_lambda_remaining_gap_prioritization(
    path: str | Path,
) -> LambdaRemainingGapPrioritization:
    return LambdaRemainingGapPrioritization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remaining_gap_prioritization(
    path: str | Path,
    report: LambdaRemainingGapPrioritization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
