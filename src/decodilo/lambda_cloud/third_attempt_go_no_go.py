"""Go/no-go record for M033 third-attempt review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.third_attempt_authorization import (
    LambdaThirdAttemptAuthorization,
    load_lambda_third_attempt_authorization,
)

LambdaThirdAttemptGoNoGoStatus = Literal[
    "no_go",
    "needs_more_evidence",
    "go_for_future_m034_third_launch_review",
]


class LambdaThirdAttemptGoNoGoRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    record_id: str = "lambda-third-attempt-go-no-go-m033"
    status: LambdaThirdAttemptGoNoGoStatus
    authorization_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_steps: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptGoNoGoRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("M033 go/no-go cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_go_no_go(
    authorization: LambdaThirdAttemptAuthorization,
) -> LambdaThirdAttemptGoNoGoRecord:
    if authorization.status == "authorized_for_future_m034_third_launch_attempt":
        status: LambdaThirdAttemptGoNoGoStatus = (
            "go_for_future_m034_third_launch_review"
        )
    elif authorization.blockers:
        status = "needs_more_evidence"
    else:
        status = "no_go"
    return LambdaThirdAttemptGoNoGoRecord(
        status=status,
        authorization_status=authorization.status,
        blockers=authorization.blockers,
        warnings=[
            "M033 go/no-go is not launch approval and cannot execute mutation",
            *authorization.warnings,
        ],
        next_required_steps=[
            "perform fresh read-only discovery before any future M034 attempt",
            "obtain explicit operator confirmation before any future M034 attempt",
            "run full verification before any future M034 attempt",
            "use response-capture diagnostics and no automatic launch retry",
        ],
    )


def build_lambda_third_attempt_go_no_go_from_path(
    authorization: str | Path,
) -> LambdaThirdAttemptGoNoGoRecord:
    return build_lambda_third_attempt_go_no_go(
        load_lambda_third_attempt_authorization(authorization)
    )


def load_lambda_third_attempt_go_no_go(
    path: str | Path,
) -> LambdaThirdAttemptGoNoGoRecord:
    return LambdaThirdAttemptGoNoGoRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_go_no_go(
    path: str | Path,
    record: LambdaThirdAttemptGoNoGoRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
