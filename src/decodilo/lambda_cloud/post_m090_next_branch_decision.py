"""M091 next-branch decision after M090 analysis."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_experiment_evidence_interpretation import (
    load_lambda_bounded_experiment_evidence_interpretation,
)
from decodilo.lambda_cloud.remaining_gap_prioritization import (
    NextBranch,
    load_lambda_remaining_gap_prioritization,
)


class LambdaPostM090NextBranchDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M091"
    decision_status: str
    recommended_branch: NextBranch
    rationale: str
    no_live_authorization: bool = True
    no_generic_smoke_category: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_decision(self) -> LambdaPostM090NextBranchDecision:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("post-M090 branch decision must remain offline")
        if self.no_live_authorization is not True:
            raise ValueError("M091 cannot authorize live execution")
        if self.decision_status == "next_branch_selected" and self.blockers:
            raise ValueError("selected next branch cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_post_m090_next_branch_decision_from_paths(
    *,
    gap_prioritization: str | Path,
    evidence_interpretation: str | Path,
) -> LambdaPostM090NextBranchDecision:
    prioritization = load_lambda_remaining_gap_prioritization(gap_prioritization)
    interpretation = load_lambda_bounded_experiment_evidence_interpretation(
        evidence_interpretation
    )
    blockers: list[str] = []
    if prioritization.prioritization_status != "remaining_gaps_prioritized":
        blockers.append("remaining_gaps_not_prioritized")
    if interpretation.interpretation_status != "evidence_interpreted":
        blockers.append("evidence_not_interpreted")
    rationale = (
        "The bounded synthetic experiment is complete, and the largest remaining "
        "scientific credibility gap is that no real training loop has run. Plan a "
        "tiny real-training smoke next, but do not authorize live execution in M091."
    )
    return LambdaPostM090NextBranchDecision(
        decision_status="next_branch_selected" if not blockers else "blocked",
        recommended_branch=prioritization.recommended_branch,
        rationale=rationale,
        blockers=blockers,
        warnings=[
            "M091 creates no immediate live authorization",
            "do not add another generic smoke category by default",
        ],
    )


def load_lambda_post_m090_next_branch_decision(
    path: str | Path,
) -> LambdaPostM090NextBranchDecision:
    return LambdaPostM090NextBranchDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_post_m090_next_branch_decision(
    path: str | Path,
    report: LambdaPostM090NextBranchDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
