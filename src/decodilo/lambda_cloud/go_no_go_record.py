"""Go/no-go design record for M025 final Lambda pre-launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_prelaunch_review import (
    LambdaFinalPrelaunchReviewReport,
    load_lambda_final_prelaunch_review,
)

LambdaGoNoGoStatus = Literal[
    "no_go",
    "blocked",
    "go_for_future_m026_real_launch_review",
]


class LambdaGoNoGoRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_schema_version: int = 1
    record_id: str = "lambda-go-no-go-record-m025"
    final_prelaunch_review_ref: str
    evidence_package_ref: str | None = None
    operator_checklist_ref: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: LambdaGoNoGoStatus
    rationale: str
    next_required_steps: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaGoNoGoRecord:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 go/no-go record cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_go_no_go_record(
    *,
    review: str | Path | LambdaFinalPrelaunchReviewReport,
    evidence_package_ref: str | Path | None = None,
    operator_checklist_ref: str | Path | None = None,
) -> LambdaGoNoGoRecord:
    if isinstance(review, LambdaFinalPrelaunchReviewReport):
        report = review
        ref = "<in-memory>"
    else:
        report = load_lambda_final_prelaunch_review(review)
        ref = str(review)
    if report.blockers:
        status: LambdaGoNoGoStatus = "blocked"
        rationale = "Final prelaunch review has blockers."
    elif report.go_no_go_recommendation == "go_for_future_m026_real_launch_review":
        status = "go_for_future_m026_real_launch_review"
        rationale = (
            "Evidence is ready for a future M026 real launch review; "
            "launch remains disabled now."
        )
    else:
        status = "no_go"
        rationale = "Final prelaunch review did not recommend future review."
    return LambdaGoNoGoRecord(
        final_prelaunch_review_ref=ref,
        evidence_package_ref=None if evidence_package_ref is None else str(evidence_package_ref),
        operator_checklist_ref=None
        if operator_checklist_ref is None
        else str(operator_checklist_ref),
        blockers=report.blockers,
        warnings=[
            "future launch review candidate only; launch remains disabled in this build",
            *report.warnings,
        ],
        status=status,
        rationale=rationale,
        next_required_steps=[
            "human review of M025 evidence",
            "explicit future milestone required before any real mutation implementation",
        ],
    )


def load_lambda_go_no_go_record(path: str | Path) -> LambdaGoNoGoRecord:
    return LambdaGoNoGoRecord.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_go_no_go_record(path: str | Path, record: LambdaGoNoGoRecord) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
