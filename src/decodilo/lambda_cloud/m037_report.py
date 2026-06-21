"""M037 combined report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m037_decision_record import (
    LambdaM037DecisionRecord,
    load_lambda_m037_decision_record,
)


class LambdaM037Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m037-support-response-and-shape-decision"
    decision: LambdaM037DecisionRecord
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM037Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M037 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m037_report(*, decision: LambdaM037DecisionRecord) -> LambdaM037Report:
    return LambdaM037Report(
        decision=decision,
        report_passed=decision.status
        in {
            "require_more_support_evidence",
            "endpoint_confirmed_reauthorize_lower_cost_shape",
            "endpoint_confirmed_keep_current_shape",
            "endpoint_contradiction_fix_implementation_first",
            "pause_launch_attempts",
        },
        blockers=decision.blockers,
        warnings=[
            "M037 is review-only and cannot authorize immediate launch",
            *decision.warnings,
        ],
    )


def build_lambda_m037_report_from_path(decision: str | Path) -> LambdaM037Report:
    return build_lambda_m037_report(decision=load_lambda_m037_decision_record(decision))


def load_lambda_m037_report(path: str | Path) -> LambdaM037Report:
    return LambdaM037Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m037_report(path: str | Path, report: LambdaM037Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
