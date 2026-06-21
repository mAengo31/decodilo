"""Envelope and error models for fake Lambda mutation-shaped responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FakeLambdaMutationAPIError(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False


class FakeLambdaMutationAPIEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    operation: str
    response: dict[str, Any] | None = None
    error: FakeLambdaMutationAPIError | None = None
    fake_only: bool = True
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_fake_only(self) -> FakeLambdaMutationAPIEnvelope:
        if not self.fake_only:
            raise ValueError("fake mutation envelope must be fake_only=true")
        if self.real_lambda_api_used or self.real_mutating_operations:
            raise ValueError("fake mutation envelope must not use real mutation")
        if self.billable_action_performed:
            raise ValueError("fake mutation envelope must not perform billable actions")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def success_envelope(operation: str, response: BaseModel) -> FakeLambdaMutationAPIEnvelope:
    return FakeLambdaMutationAPIEnvelope(
        ok=True,
        operation=operation,
        response=response.model_dump(mode="json"),
    )


def error_envelope(operation: str, code: str, message: str) -> FakeLambdaMutationAPIEnvelope:
    return FakeLambdaMutationAPIEnvelope(
        ok=False,
        operation=operation,
        error=FakeLambdaMutationAPIError(code=code, message=message),
    )
