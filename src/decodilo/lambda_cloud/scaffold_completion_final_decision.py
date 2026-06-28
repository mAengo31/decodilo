"""M090 final scaffold-completion decision after M089R."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_closeout import (
    load_lambda_bounded_diloco_experiment_closeout,
)
from decodilo.lambda_cloud.scaffold_complete_decision import (
    load_lambda_scaffold_complete_decision,
)

LambdaScaffoldFinalStatus = Literal["complete", "incomplete"]


class LambdaScaffoldCompletionFinalDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
    scaffold_final_status: LambdaScaffoldFinalStatus
    bounded_experiment_completed: bool
    prior_scaffold_validation_complete: bool
    no_more_scaffold_categories_by_default: bool = True
    next_phase: str = "scientific_extension_or_real_training_planning"
    future_live_work_requires_new_scientific_plan: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_decision(self) -> LambdaScaffoldCompletionFinalDecision:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("scaffold final decision must remain offline")
        if self.scaffold_final_status == "complete" and self.blockers:
            raise ValueError("complete scaffold final decision cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_scaffold_completion_final_decision_from_paths(
    *,
    bounded_closeout: str | Path,
    scaffold_decision: str | Path,
) -> LambdaScaffoldCompletionFinalDecision:
    closeout = load_lambda_bounded_diloco_experiment_closeout(bounded_closeout)
    scaffold = load_lambda_scaffold_complete_decision(scaffold_decision)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("bounded_experiment_closeout_not_succeeded")
    if scaffold.scaffold_status != "scaffold_validation_complete":
        blockers.append("prior_scaffold_validation_not_complete")
    if closeout.launch_ready or closeout.launch_allowed:
        blockers.append("bounded_closeout_launch_flags_enabled")
    bounded_complete = closeout.closeout_succeeded
    prior_complete = scaffold.scaffold_status == "scaffold_validation_complete"
    return LambdaScaffoldCompletionFinalDecision(
        scaffold_final_status="complete" if not blockers else "incomplete",
        bounded_experiment_completed=bounded_complete,
        prior_scaffold_validation_complete=prior_complete,
        blockers=blockers,
        warnings=[
            "M090 closes scaffold validation after the first complete bounded "
            "synthetic DiLoCo experiment",
            "future work should be selected as a scientific extension or real "
            "training plan, not a new scaffold category by default",
        ],
    )


def load_lambda_scaffold_completion_final_decision(
    path: str | Path,
) -> LambdaScaffoldCompletionFinalDecision:
    return LambdaScaffoldCompletionFinalDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_scaffold_completion_final_decision(
    path: str | Path,
    report: LambdaScaffoldCompletionFinalDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
