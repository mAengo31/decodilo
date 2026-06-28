"""Future-only Python runtime command policy for M065 planning."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M065_PYTHON_RUNTIME_COMMAND = "python3 --version"

LambdaPythonRuntimeCommandPolicyStatus = Literal[
    "python_runtime_command_policy_defined_future_only",
    "blocked",
]

_FORBIDDEN_SUBSTRINGS = (
    ";",
    "|",
    "&&",
    "||",
    "`",
    "$(",
    "\n",
    "\r",
    " -c",
    " -m",
    ".py",
    " import",
    " exec",
    " eval",
    " pip",
    " conda",
    " apt",
    " install",
    " train",
    " nvidia-smi",
    " scp",
    " sftp",
    " rsync",
)


class LambdaPythonRuntimeCommandPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy_status: LambdaPythonRuntimeCommandPolicyStatus
    allowed_future_stage: str = "python_version_query_only"
    allowed_future_command: str = M065_PYTHON_RUNTIME_COMMAND
    selected_future_command_set: list[str] = Field(default_factory=list)
    fallback_allowed: bool = False
    max_remote_commands: int = 1
    future_only: bool = True
    command_execution_allowed_now: bool = False
    python_script_allowed: bool = False
    python_module_execution_allowed: bool = False
    python_inline_code_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    shell_wrapper_allowed: bool = False
    command_chaining_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    forbidden_patterns: list[str] = Field(
        default_factory=lambda: list(_FORBIDDEN_SUBSTRINGS)
    )
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaPythonRuntimeCommandPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_execution_allowed_now
            or not self.future_only
            or self.fallback_allowed
            or self.max_remote_commands != 1
            or self.python_script_allowed
            or self.python_module_execution_allowed
            or self.python_inline_code_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.shell_wrapper_allowed
            or self.command_chaining_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("Python runtime command policy cannot enable execution")
        if self.policy_status == "python_runtime_command_policy_defined_future_only":
            if self.blockers or self.selected_future_command_set != [
                self.allowed_future_command
            ]:
                raise ValueError("Python runtime command policy requires exact command")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_python_runtime_command(command: str) -> bool:
    if command != M065_PYTHON_RUNTIME_COMMAND:
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if argv != ["python3", "--version"]:
        return False
    lowered = f" {command.lower()} "
    return not any(token in lowered for token in _FORBIDDEN_SUBSTRINGS)


def build_lambda_python_runtime_command_policy() -> LambdaPythonRuntimeCommandPolicy:
    blockers = []
    if not validate_python_runtime_command(M065_PYTHON_RUNTIME_COMMAND):
        blockers.append("exact_python_runtime_command_invalid")
    status: LambdaPythonRuntimeCommandPolicyStatus = (
        "python_runtime_command_policy_defined_future_only" if not blockers else "blocked"
    )
    return LambdaPythonRuntimeCommandPolicy(
        policy_status=status,
        selected_future_command_set=(
            [M065_PYTHON_RUNTIME_COMMAND] if status != "blocked" else []
        ),
        blockers=blockers,
        warnings=[
            "M064 defines only a future M065 python3 --version query",
            "Python scripts, inline code, imports, package installs, and training remain forbidden",
        ],
    )


def load_lambda_python_runtime_command_policy(
    path: str | Path,
) -> LambdaPythonRuntimeCommandPolicy:
    return LambdaPythonRuntimeCommandPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_python_runtime_command_policy(
    path: str | Path,
    report: LambdaPythonRuntimeCommandPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
