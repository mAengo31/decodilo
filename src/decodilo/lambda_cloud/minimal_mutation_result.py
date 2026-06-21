"""Minimal fake-server mutation result models for M027."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaMinimalMutationError(BaseModel):
    model_config = ConfigDict(frozen=True)

    error_type: str
    message: str
    recoverable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LambdaMinimalMutationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operation: Literal["launch_one_instance", "terminate_owned_instance"]
    success: bool
    idempotency_key: str | None = None
    fake_server_only: bool = True
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: LambdaMinimalMutationError | None = None

    @model_validator(mode="after")
    def _m027_flags_false(self) -> LambdaMinimalMutationResult:
        if (
            not self.fake_server_only
            or self.real_lambda_api_used
            or self.real_mutating_operations
            or self.billable_action_performed
            or self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
        ):
            raise ValueError("M027 minimal mutation result must remain fake/local only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMinimalLaunchResult(LambdaMinimalMutationResult):
    operation: Literal["launch_one_instance"] = "launch_one_instance"
    instance_id: str
    lifecycle_state: str = "running"

    @model_validator(mode="after")
    def _synthetic_instance(self) -> LambdaMinimalLaunchResult:
        if not self.instance_id.startswith("fake-i-"):
            raise ValueError("M027 fake launch result requires synthetic fake-i-* id")
        return self


class LambdaMinimalTerminateResult(LambdaMinimalMutationResult):
    operation: Literal["terminate_owned_instance"] = "terminate_owned_instance"
    instance_id: str
    lifecycle_state: str = "terminated"
    termination_verified: bool = False

    @model_validator(mode="after")
    def _synthetic_instance(self) -> LambdaMinimalTerminateResult:
        if not self.instance_id.startswith("fake-i-"):
            raise ValueError("M027 fake terminate result requires synthetic fake-i-* id")
        return self


def write_lambda_minimal_mutation_result(
    path: str | Path,
    result: LambdaMinimalMutationResult,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(), encoding="utf-8")
