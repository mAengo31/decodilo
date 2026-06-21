"""M043 capacity follow-up report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m043_decision_record import (
    load_lambda_m043_decision_record,
)


class LambdaM043Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: str
    selected_shape: str | None = None
    selected_region: str | None = None
    estimated_30min_cost: float | None = None
    buffered_30min_cost: float | None = None
    future_review_allowed: bool
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM043Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M043 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m043_report_from_path(decision: str | Path) -> LambdaM043Report:
    record = load_lambda_m043_decision_record(decision)
    return LambdaM043Report(
        decision_status=record.decision_status,
        selected_shape=record.selected_shape,
        selected_region=record.selected_region,
        estimated_30min_cost=record.estimated_30min_cost,
        buffered_30min_cost=record.buffered_30min_cost,
        future_review_allowed=record.future_review_allowed,
        report_passed=not record.blockers,
        blockers=record.blockers,
        warnings=[
            "M043 report is review-only",
            "future launch review requires a new supervised milestone",
            *record.warnings,
        ],
    )


def load_lambda_m043_report(path: str | Path) -> LambdaM043Report:
    return LambdaM043Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m043_report(path: str | Path, report: LambdaM043Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
