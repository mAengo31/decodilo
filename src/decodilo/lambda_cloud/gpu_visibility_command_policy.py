"""Future-only GPU visibility command policy for M063 planning."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M063_GPU_VISIBILITY_COMMAND = (
    "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader"
)

LambdaGPUVisibilityCommandPolicyStatus = Literal[
    "gpu_visibility_command_policy_defined_future_only",
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
    " watch ",
    " dmon",
    " topo",
    " nvlink",
    " gpu-reset",
    " python",
    " apt",
    " pip",
    " conda",
    " git",
    " docker",
    " stress",
    " benchmark",
    " train",
    " scp",
    " sftp",
    " rsync",
    " -l",
    "--loop",
)


class LambdaGPUVisibilityCommandPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    command_policy_status: LambdaGPUVisibilityCommandPolicyStatus
    allowed_future_stage: str = "gpu_visibility_query_only"
    exact_command: str = M063_GPU_VISIBILITY_COMMAND
    selected_future_command_set: list[str] = Field(default_factory=list)
    future_only: bool = True
    command_execution_allowed_now: bool = False
    raw_nvidia_smi_allowed: bool = False
    looping_allowed: bool = False
    shell_wrapper_allowed: bool = False
    command_chaining_allowed: bool = False
    python_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    benchmark_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaGPUVisibilityCommandPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_execution_allowed_now
            or not self.future_only
            or self.raw_nvidia_smi_allowed
            or self.looping_allowed
            or self.shell_wrapper_allowed
            or self.command_chaining_allowed
            or self.python_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.benchmark_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("GPU visibility command policy cannot enable execution")
        if self.command_policy_status == "gpu_visibility_command_policy_defined_future_only":
            if self.blockers or self.selected_future_command_set != [self.exact_command]:
                raise ValueError("GPU visibility command policy requires exact command only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_gpu_visibility_command(command: str) -> bool:
    if command != M063_GPU_VISIBILITY_COMMAND:
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if argv != [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader",
    ]:
        return False
    lowered = f" {command.lower()} "
    return not any(token in lowered for token in _FORBIDDEN_SUBSTRINGS)


def build_lambda_gpu_visibility_command_policy() -> LambdaGPUVisibilityCommandPolicy:
    blockers = []
    if not validate_gpu_visibility_command(M063_GPU_VISIBILITY_COMMAND):
        blockers.append("exact_gpu_visibility_command_invalid")
    status: LambdaGPUVisibilityCommandPolicyStatus = (
        "gpu_visibility_command_policy_defined_future_only" if not blockers else "blocked"
    )
    return LambdaGPUVisibilityCommandPolicy(
        command_policy_status=status,
        selected_future_command_set=(
            [M063_GPU_VISIBILITY_COMMAND] if status != "blocked" else []
        ),
        blockers=blockers,
        warnings=[
            "M062 defines a future M063 GPU visibility query only",
            "The exact command is not executable in M062",
            (
                "Training, installation, shell wrappers, loops, benchmarks, "
                "transfers, and port forwarding remain forbidden"
            ),
        ],
    )


def load_lambda_gpu_visibility_command_policy(
    path: str | Path,
) -> LambdaGPUVisibilityCommandPolicy:
    return LambdaGPUVisibilityCommandPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_command_policy(
    path: str | Path,
    report: LambdaGPUVisibilityCommandPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
