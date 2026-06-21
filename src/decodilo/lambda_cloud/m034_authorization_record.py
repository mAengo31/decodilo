"""Future-M034-only authorization record for a third Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaM034AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m034_third_launch_attempt",
]


class LambdaM034AuthorizationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    record_id: str = "lambda-m034-authorization-record"
    status: LambdaM034AuthorizationStatus
    authorized_for: str = "future_m034_third_launch_attempt"
    authorized_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_authorized_now: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM034AuthorizationRecord:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("M034 authorization record cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034_authorization_record(
    *,
    status: LambdaM034AuthorizationStatus,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
) -> LambdaM034AuthorizationRecord:
    authorized = status == "authorized_for_future_m034_third_launch_attempt"
    return LambdaM034AuthorizationRecord(
        status=status,
        authorized_operations=[
            "future launch_one_instance attempt only",
            "future read-only running verification",
            "future terminate exact/high-confidence owned instance only",
            "future read-only termination verification",
        ]
        if authorized
        else [],
        forbidden_operations=[
            "launch now",
            "terminate now",
            "restart",
            "create/delete SSH key",
            "create/delete filesystem",
            "SSH",
            "setup scripts",
            "cloud-init",
            "training",
            "background execution",
            "automatic launch retry after response loss",
            "terminate medium/low/no-confidence candidates",
        ],
        blockers=blockers or [],
        warnings=[
            "M034 record is for future review only; M033 does not execute",
            *(warnings or []),
        ],
    )


def load_lambda_m034_authorization_record(
    path: str | Path,
) -> LambdaM034AuthorizationRecord:
    return LambdaM034AuthorizationRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_authorization_record(
    path: str | Path,
    record: LambdaM034AuthorizationRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
