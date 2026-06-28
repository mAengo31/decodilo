"""Future-only remote command stage policy after M057."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RemoteCommandStage = Literal[
    "no_remote_command",
    "noop_command_only",
    "identity_command",
    "gpu_visibility_command",
    "python_version_command",
    "decodilo_cli_version_command",
    "runtime_smoke_command",
    "training_command",
]


class LambdaRemoteCommandStagePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy_status: Literal["policy_defined", "blocked"] = "policy_defined"
    current_accepted_stage: RemoteCommandStage = "noop_command_only"
    allowed_future_review_stages: list[RemoteCommandStage] = Field(
        default_factory=lambda: ["identity_command"]
    )
    training_command_allowed: bool = False
    package_install_allowed: bool = False
    arbitrary_shell_allowed: bool = False
    command_chaining_allowed: bool = False
    pipes_allowed: bool = False
    redirects_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    immediate_execution_authorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteCommandStagePolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.training_command_allowed
            or self.package_install_allowed
            or self.arbitrary_shell_allowed
            or self.command_chaining_allowed
            or self.pipes_allowed
            or self.redirects_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.immediate_execution_authorized
        ):
            raise ValueError("remote command stage policy cannot authorize execution")
        if self.current_accepted_stage != "noop_command_only":
            raise ValueError("M058 current accepted stage must be noop_command_only")
        if "training_command" in self.allowed_future_review_stages:
            raise ValueError("training command cannot be allowed for future review here")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_command_stage_policy() -> LambdaRemoteCommandStagePolicy:
    return LambdaRemoteCommandStagePolicy(
        warnings=[
            "M058 can authorize only future review, not immediate command execution",
            "training, package install, shell composition, transfer, and forwarding "
            "remain forbidden",
        ]
    )


def load_lambda_remote_command_stage_policy(
    path: str | Path,
) -> LambdaRemoteCommandStagePolicy:
    return LambdaRemoteCommandStagePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_command_stage_policy(
    path: str | Path,
    report: LambdaRemoteCommandStagePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
