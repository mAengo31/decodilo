"""Future-only remote command allowlist for Lambda bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRemoteCommandAllowlistProfile = Literal[
    "metadata-only",
    "connectivity-only",
    "gpu-visibility-check",
    "python-version-check",
    "decodilo-version-check",
]

SAFE_COMMANDS_BY_PROFILE: dict[LambdaRemoteCommandAllowlistProfile, list[str]] = {
    "metadata-only": [],
    "connectivity-only": ["hostname"],
    "gpu-visibility-check": [
        "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader"
    ],
    "python-version-check": ["python3 --version"],
    "decodilo-version-check": ["python -m decodilo.cli --version"],
}

FORBIDDEN_COMMAND_TOKENS = (
    ";",
    "|",
    ">",
    "<",
    "&&",
    "||",
    "`",
    "$(",
    "curl",
    "wget",
    "apt",
    "pip",
    "conda",
    "git",
    "docker",
    "nohup",
    "torchrun",
    "accelerate",
    "train",
    "&",
)


class LambdaRemoteCommandAllowlistReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    command_allowlist_status: Literal["allowlist_defined_future_only", "blocked"]
    profile: LambdaRemoteCommandAllowlistProfile
    commands: list[str] = Field(default_factory=list)
    future_only: bool = True
    command_execution_allowed_now: bool = False
    no_shell_chaining: bool = True
    no_package_install_commands: bool = True
    no_training_commands: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteCommandAllowlistReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_execution_allowed_now
            or not self.future_only
            or not self.no_shell_chaining
            or not self.no_package_install_commands
            or not self.no_training_commands
        ):
            raise ValueError("remote command allowlist cannot enable command execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaRemoteCommandAllowlist = LambdaRemoteCommandAllowlistReport


def build_lambda_remote_command_allowlist(
    *,
    profile: LambdaRemoteCommandAllowlistProfile = "metadata-only",
) -> LambdaRemoteCommandAllowlistReport:
    commands = SAFE_COMMANDS_BY_PROFILE[profile]
    blockers = [
        f"unsafe_command:{command}"
        for command in commands
        if not validate_future_remote_command(command)
    ]
    return LambdaRemoteCommandAllowlistReport(
        command_allowlist_status=(
            "allowlist_defined_future_only" if not blockers else "blocked"
        ),
        profile=profile,
        commands=commands,
        blockers=blockers,
        warnings=[
            "allowlisted commands are planned only in M050 and are not executed",
            "remote command execution requires a later supervised milestone",
            "M053 SSH connectivity-only planning requires an empty command surface",
            "M058 opens only a future M059 identity-command review",
            "M062 opens only a future M063 GPU visibility query review",
            "M064 opens only a future M065 python3 --version runtime query review",
        ],
    )


def validate_future_remote_command(command: str) -> bool:
    lowered = f" {command.lower()} "
    if command not in {
        safe for commands in SAFE_COMMANDS_BY_PROFILE.values() for safe in commands
    }:
        return False
    return not any(token in lowered for token in FORBIDDEN_COMMAND_TOKENS)


def load_lambda_remote_command_allowlist(
    path: str | Path,
) -> LambdaRemoteCommandAllowlistReport:
    return LambdaRemoteCommandAllowlistReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_command_allowlist(
    path: str | Path,
    report: LambdaRemoteCommandAllowlistReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
