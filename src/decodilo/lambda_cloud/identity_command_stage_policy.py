"""Remote identity-command stage policy after M061."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaIdentityCommandStagePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    stage_policy_status: str = "identity_command_stage_closed_future_only"
    completed_commands: list[str] = Field(default_factory=lambda: ["true", "hostname", "whoami"])
    next_future_stage: str = "gpu_visibility_query_only"
    future_only: bool = True
    command_execution_allowed_now: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaIdentityCommandStagePolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_execution_allowed_now
            or not self.future_only
        ):
            raise ValueError("identity command stage policy cannot enable execution")
        if self.completed_commands != ["true", "hostname", "whoami"]:
            raise ValueError("identity command stage policy has a fixed completed set")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_identity_command_stage_policy() -> LambdaIdentityCommandStagePolicy:
    return LambdaIdentityCommandStagePolicy(
        warnings=[
            "M061 completed the identity-command ladder",
            "M063 GPU visibility remains future-only and requires separate authorization",
        ]
    )


def load_lambda_identity_command_stage_policy(
    path: str | Path,
) -> LambdaIdentityCommandStagePolicy:
    return LambdaIdentityCommandStagePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_identity_command_stage_policy(
    path: str | Path,
    report: LambdaIdentityCommandStagePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
