"""Future-only command review for M063 GPU visibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    M063_GPU_VISIBILITY_COMMAND,
    load_lambda_gpu_visibility_command_policy,
    validate_gpu_visibility_command,
)
from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    load_lambda_gpu_visibility_output_policy,
)

LambdaGPUVisibilityCommandReviewStatus = Literal[
    "gpu_visibility_command_review_passed_future_only",
    "blocked",
]


class LambdaGPUVisibilityCommandReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    command_review_status: LambdaGPUVisibilityCommandReviewStatus
    selected_future_command_set: list[str] = Field(default_factory=list)
    selected_command: str | None = None
    command_risk_level: str | None = None
    output_capture_bounded: bool
    no_shell_wrapper: bool = True
    no_command_chaining: bool = True
    no_package_install: bool = True
    no_training: bool = True
    no_benchmark: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    command_authorized_now: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaGPUVisibilityCommandReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_authorized_now
            or not self.no_shell_wrapper
            or not self.no_command_chaining
            or not self.no_package_install
            or not self.no_training
            or not self.no_benchmark
            or not self.no_file_transfer
            or not self.no_port_forwarding
        ):
            raise ValueError("M063 command review cannot authorize immediate execution")
        if self.command_review_status == "gpu_visibility_command_review_passed_future_only":
            if (
                self.blockers
                or self.selected_command != M063_GPU_VISIBILITY_COMMAND
                or self.selected_future_command_set != [M063_GPU_VISIBILITY_COMMAND]
            ):
                raise ValueError("M063 command review requires exact future command")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_command_review_from_paths(
    *,
    command_policy: str | Path,
    output_policy: str | Path,
) -> LambdaGPUVisibilityCommandReview:
    command = load_lambda_gpu_visibility_command_policy(command_policy)
    output = load_lambda_gpu_visibility_output_policy(output_policy)
    blockers = [*command.blockers, *output.blockers]
    if (
        command.command_policy_status
        != "gpu_visibility_command_policy_defined_future_only"
    ):
        blockers.append("command_policy_not_passed")
    if output.output_policy_status != "gpu_visibility_output_policy_defined_future_only":
        blockers.append("output_policy_not_passed")
    if not validate_gpu_visibility_command(command.exact_command):
        blockers.append("gpu_visibility_command_not_exact_safe_query")
    if output.max_stdout_bytes > 4096 or output.max_stderr_bytes > 4096:
        blockers.append("output_capture_not_bounded")
    status: LambdaGPUVisibilityCommandReviewStatus = (
        "gpu_visibility_command_review_passed_future_only" if not blockers else "blocked"
    )
    return LambdaGPUVisibilityCommandReview(
        command_review_status=status,
        selected_future_command_set=(
            [M063_GPU_VISIBILITY_COMMAND] if status != "blocked" else []
        ),
        selected_command=(M063_GPU_VISIBILITY_COMMAND if status != "blocked" else None),
        command_risk_level=("low_diagnostic_query" if status != "blocked" else None),
        output_capture_bounded=(
            output.max_stdout_bytes <= 4096 and output.max_stderr_bytes <= 4096
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M062 reviews only a future M063 GPU visibility query",
            "The reviewed command is not executable in M062",
        ],
    )


def load_lambda_gpu_visibility_command_review(
    path: str | Path,
) -> LambdaGPUVisibilityCommandReview:
    return LambdaGPUVisibilityCommandReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_command_review(
    path: str | Path,
    report: LambdaGPUVisibilityCommandReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
