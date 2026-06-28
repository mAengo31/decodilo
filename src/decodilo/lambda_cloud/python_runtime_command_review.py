"""Future-only command review for the M065 Python runtime query."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.python_runtime_command_policy import (
    M065_PYTHON_RUNTIME_COMMAND,
    load_lambda_python_runtime_command_policy,
    validate_python_runtime_command,
)
from decodilo.lambda_cloud.python_runtime_output_policy import (
    load_lambda_python_runtime_output_policy,
)

LambdaPythonRuntimeCommandReviewStatus = Literal[
    "python_runtime_command_review_passed_future_only",
    "blocked",
]


class LambdaPythonRuntimeCommandReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    command_review_status: LambdaPythonRuntimeCommandReviewStatus
    selected_future_command_set: list[str] = Field(default_factory=list)
    selected_command: str | None = None
    command_risk_level: str | None = None
    output_capture_bounded: bool
    no_shell_wrapper: bool = True
    no_command_chaining: bool = True
    no_package_install: bool = True
    no_training: bool = True
    no_imports: bool = True
    no_script_execution: bool = True
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
    def _validate_future_only(self) -> LambdaPythonRuntimeCommandReview:
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
            or not self.no_imports
            or not self.no_script_execution
            or not self.no_file_transfer
            or not self.no_port_forwarding
        ):
            raise ValueError("M065 command review cannot authorize immediate execution")
        if self.command_review_status == "python_runtime_command_review_passed_future_only":
            if (
                self.blockers
                or self.selected_command != M065_PYTHON_RUNTIME_COMMAND
                or self.selected_future_command_set != [M065_PYTHON_RUNTIME_COMMAND]
            ):
                raise ValueError("M065 command review requires exact future command")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_python_runtime_command_review_from_paths(
    *,
    command_policy: str | Path,
    output_policy: str | Path,
) -> LambdaPythonRuntimeCommandReview:
    command = load_lambda_python_runtime_command_policy(command_policy)
    output = load_lambda_python_runtime_output_policy(output_policy)
    blockers = [*command.blockers, *output.blockers]
    if command.policy_status != "python_runtime_command_policy_defined_future_only":
        blockers.append("command_policy_not_passed")
    if output.output_policy_status != "python_runtime_output_policy_defined_future_only":
        blockers.append("output_policy_not_passed")
    if not validate_python_runtime_command(command.allowed_future_command):
        blockers.append("python_runtime_command_not_exact_safe_query")
    if output.max_stdout_bytes > 1024 or output.max_stderr_bytes > 2048:
        blockers.append("output_capture_not_bounded")
    status: LambdaPythonRuntimeCommandReviewStatus = (
        "python_runtime_command_review_passed_future_only" if not blockers else "blocked"
    )
    return LambdaPythonRuntimeCommandReview(
        command_review_status=status,
        selected_future_command_set=(
            [M065_PYTHON_RUNTIME_COMMAND] if status != "blocked" else []
        ),
        selected_command=(M065_PYTHON_RUNTIME_COMMAND if status != "blocked" else None),
        command_risk_level=("low_diagnostic_version_query" if status != "blocked" else None),
        output_capture_bounded=(
            output.max_stdout_bytes <= 1024 and output.max_stderr_bytes <= 2048
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M064 reviews only a future M065 Python version query",
            "The reviewed command is not executable in M064",
        ],
    )


def load_lambda_python_runtime_command_review(
    path: str | Path,
) -> LambdaPythonRuntimeCommandReview:
    return LambdaPythonRuntimeCommandReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_python_runtime_command_review(
    path: str | Path,
    report: LambdaPythonRuntimeCommandReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
