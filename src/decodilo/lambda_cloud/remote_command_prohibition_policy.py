"""Remote command prohibition for SSH-connectivity-only Lambda review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_REMOTE_COMMAND_TOKENS = (
    "nvidia-smi",
    "python",
    "bash",
    "sh ",
    "sudo",
    "apt",
    "pip",
    "conda",
    "torchrun",
    "train",
)


class LambdaRemoteCommandProhibitionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prohibition_status: str = "remote_commands_prohibited"
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    command_allowlist_must_be_empty: bool = True
    nvidia_smi_allowed: bool = False
    python_allowed: bool = False
    shell_allowed: bool = False
    command_string_allowed: bool = False
    stdin_allowed: bool = False
    tty_allowed: bool = False
    proposed_commands: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_commands(self) -> LambdaRemoteCommandProhibitionPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.remote_exec_allowed
            or self.interactive_shell_allowed
            or not self.command_allowlist_must_be_empty
            or self.nvidia_smi_allowed
            or self.python_allowed
            or self.shell_allowed
            or self.command_string_allowed
            or self.stdin_allowed
            or self.tty_allowed
            or self.proposed_commands
        ):
            raise ValueError("remote command prohibition cannot allow commands")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def remote_command_blockers_for(command: str) -> list[str]:
    lowered = f" {command.lower()} "
    blockers = ["remote_command_string_present"]
    blockers.extend(
        f"forbidden_remote_command_token:{token.strip()}"
        for token in FORBIDDEN_REMOTE_COMMAND_TOKENS
        if token in lowered
    )
    return sorted(set(blockers))


def build_lambda_remote_command_prohibition_policy() -> LambdaRemoteCommandProhibitionPolicy:
    return LambdaRemoteCommandProhibitionPolicy(
        warnings=["M053 SSH connectivity-only review prohibits remote commands and shells"],
    )


def load_lambda_remote_command_prohibition_policy(
    path: str | Path,
) -> LambdaRemoteCommandProhibitionPolicy:
    return LambdaRemoteCommandProhibitionPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_command_prohibition_policy(
    path: str | Path,
    report: LambdaRemoteCommandProhibitionPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
