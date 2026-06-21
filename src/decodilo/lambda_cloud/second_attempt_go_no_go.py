"""Go/no-go record for M030 second-attempt review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.second_attempt_authorization import (
    LambdaSecondAttemptAuthorization,
    load_lambda_second_attempt_authorization,
)

LambdaSecondAttemptGoNoGoStatus = Literal[
    "no_go",
    "needs_more_evidence",
    "go_for_future_m031_second_launch_review",
]


class LambdaSecondAttemptGoNoGoRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    record_id: str = "lambda-second-attempt-go-no-go-m030"
    status: LambdaSecondAttemptGoNoGoStatus
    authorization_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_steps: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptGoNoGoRecord:
        if self.launch_ready or self.launch_allowed or self.real_mutation_enabled:
            raise ValueError("M030 go/no-go cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_go_no_go(
    authorization: LambdaSecondAttemptAuthorization,
) -> LambdaSecondAttemptGoNoGoRecord:
    if authorization.status == "authorized_for_future_m031_second_launch_attempt":
        status: LambdaSecondAttemptGoNoGoStatus = (
            "go_for_future_m031_second_launch_review"
        )
    elif authorization.blockers:
        status = "needs_more_evidence"
    else:
        status = "no_go"
    return LambdaSecondAttemptGoNoGoRecord(
        status=status,
        authorization_status=authorization.status,
        blockers=authorization.blockers,
        warnings=[
            "M030 go/no-go is not launch approval and cannot execute mutation",
            *authorization.warnings,
        ],
        next_required_steps=[
            "perform fresh read-only discovery before any future M031 attempt",
            "obtain explicit operator confirmation before any future M031 attempt",
            "run full verification before any future M031 attempt",
        ],
    )


def build_lambda_second_attempt_go_no_go_from_path(
    authorization: str | Path,
) -> LambdaSecondAttemptGoNoGoRecord:
    return build_lambda_second_attempt_go_no_go(
        load_lambda_second_attempt_authorization(authorization)
    )


def load_lambda_second_attempt_go_no_go(path: str | Path) -> LambdaSecondAttemptGoNoGoRecord:
    return LambdaSecondAttemptGoNoGoRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_go_no_go(
    path: str | Path,
    record: LambdaSecondAttemptGoNoGoRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
