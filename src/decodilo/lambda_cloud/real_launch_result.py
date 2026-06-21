"""M029 real/fake launch and termination result models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaM029LaunchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operation: Literal["launch_one_instance"] = "launch_one_instance"
    request_sent: bool
    response_received: bool
    owned_instance_id: str | None = None
    idempotency_key: str
    lifecycle_state: str | None = None
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    manual_review_required: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _owned_id_required_on_success(self) -> LambdaM029LaunchResult:
        if (
            self.response_received
            and self.request_sent
            and not self.owned_instance_id
            and not self.manual_review_required
        ):
            raise ValueError("launch response requires owned instance id")
        return self

    @property
    def owned_instance_id_redacted(self) -> str | None:
        return redact_instance_id(self.owned_instance_id)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM029TerminationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operation: Literal["terminate_owned_instance"] = "terminate_owned_instance"
    request_sent: bool
    response_received: bool
    owned_instance_id: str
    idempotency_key: str
    lifecycle_state: str | None = None
    termination_verified: bool = False
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    manual_review_required: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def owned_instance_id_redacted(self) -> str:
        return redact_instance_id(self.owned_instance_id) or "<redacted>"

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def redact_instance_id(instance_id: str | None) -> str | None:
    if not instance_id:
        return None
    if instance_id.startswith("fake-i-"):
        return instance_id
    if len(instance_id) <= 10:
        return instance_id[:2] + "...redacted"
    return instance_id[:6] + "..." + instance_id[-4:]


def write_lambda_m029_launch_result(path: str | Path, result: LambdaM029LaunchResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(), encoding="utf-8")


def write_lambda_m029_termination_result(
    path: str | Path,
    result: LambdaM029TerminationResult,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(), encoding="utf-8")
