"""Readiness for the tiny real-training branch after M091."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m091_report import load_lambda_m091_report

LambdaTinyRealTrainingReadinessStatus = Literal[
    "ready_for_future_tiny_real_training_planning",
    "not_ready",
]


class LambdaTinyRealTrainingReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    readiness_status: LambdaTinyRealTrainingReadinessStatus
    scaffold_completion_status: str
    bounded_synthetic_experiment_completed: bool
    next_branch: str
    no_live_authorization: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaTinyRealTrainingReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny real training readiness must remain offline")
        if self.no_live_authorization is not True:
            raise ValueError("M092 readiness cannot authorize live execution")
        if (
            self.readiness_status == "ready_for_future_tiny_real_training_planning"
            and self.blockers
        ):
            raise ValueError("ready tiny real training readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_tiny_real_training_readiness_from_path(
    *,
    m091_report: str | Path,
) -> LambdaTinyRealTrainingReadiness:
    report = load_lambda_m091_report(m091_report)
    blockers: list[str] = []
    if not report.report_passed:
        blockers.append("m091_report_not_passed")
    if report.scaffold_completion_status != "complete":
        blockers.append("scaffold_not_complete")
    if report.recommended_next_branch != "plan_tiny_real_training_smoke":
        blockers.append("m091_next_branch_not_tiny_real_training")
    if not report.no_live_authorization:
        blockers.append("m091_live_authorization_present")
    ready = not blockers
    return LambdaTinyRealTrainingReadiness(
        readiness_status=(
            "ready_for_future_tiny_real_training_planning" if ready else "not_ready"
        ),
        scaffold_completion_status=report.scaffold_completion_status,
        bounded_synthetic_experiment_completed=(
            report.scaffold_completion_status == "complete"
        ),
        next_branch=report.recommended_next_branch,
        blockers=blockers,
        warnings=[
            "readiness is offline planning only and does not authorize M093R",
        ],
    )


def load_lambda_tiny_real_training_readiness(
    path: str | Path,
) -> LambdaTinyRealTrainingReadiness:
    return LambdaTinyRealTrainingReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_real_training_readiness(
    path: str | Path,
    report: LambdaTinyRealTrainingReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
