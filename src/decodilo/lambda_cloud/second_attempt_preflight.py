"""M030 second-attempt preflight summary."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.second_attempt_authorization import (
    LambdaSecondAttemptAuthorization,
)
from decodilo.lambda_cloud.second_attempt_go_no_go import LambdaSecondAttemptGoNoGoRecord


class LambdaSecondAttemptPreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preflight_passed_for_review: bool
    authorization_status: str
    go_no_go_status: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptPreflightReport:
        if self.launch_ready or self.launch_allowed or self.real_mutation_enabled:
            raise ValueError("M030 preflight cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_preflight(
    *,
    authorization: LambdaSecondAttemptAuthorization,
    go_no_go: LambdaSecondAttemptGoNoGoRecord | None = None,
) -> LambdaSecondAttemptPreflightReport:
    passed = authorization.status == "authorized_for_future_m031_second_launch_attempt"
    if go_no_go is not None:
        passed = passed and go_no_go.status == "go_for_future_m031_second_launch_review"
    return LambdaSecondAttemptPreflightReport(
        preflight_passed_for_review=passed,
        authorization_status=authorization.status,
        go_no_go_status=go_no_go.status if go_no_go else None,
        blockers=[*authorization.blockers, *(go_no_go.blockers if go_no_go else [])],
        warnings=[
            "M030 preflight is review-only; launch_ready=false and launch_allowed=false",
            *authorization.warnings,
            *(go_no_go.warnings if go_no_go else []),
        ],
    )


def load_lambda_second_attempt_preflight(
    path: str | Path,
) -> LambdaSecondAttemptPreflightReport:
    return LambdaSecondAttemptPreflightReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_preflight(
    path: str | Path,
    report: LambdaSecondAttemptPreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
