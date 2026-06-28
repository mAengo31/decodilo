"""Non-executable runbook preview for future M063 GPU visibility query."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import M063_GPU_VISIBILITY_COMMAND
from decodilo.lambda_cloud.m063_gpu_visibility_authorization import (
    load_lambda_m063_gpu_visibility_authorization,
)

LambdaM063GPUVisibilityRunbookPreviewStatus = Literal[
    "ready_for_future_m063_gpu_visibility_query_review",
    "blocked",
]


class LambdaM063GPUVisibilityRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaM063GPUVisibilityRunbookPreviewStatus
    executable: bool = False
    future_milestone: str = "M063"
    selected_command: str | None = None
    selected_future_command_set: list[str] = Field(default_factory=list)
    max_instances: int = 1
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    ssh_required_for_future_command: bool = True
    interactive_shell_allowed: bool = False
    shell_wrapper_allowed: bool = False
    command_chaining_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    termination_required: bool = True
    termination_verification_required: bool = True
    command_preview: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaM063GPUVisibilityRunbookPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.interactive_shell_allowed
            or self.shell_wrapper_allowed
            or self.command_chaining_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("M063 runbook preview must remain non-executable")
        if self.preview_status == "ready_for_future_m063_gpu_visibility_query_review":
            if (
                self.blockers
                or self.selected_command != M063_GPU_VISIBILITY_COMMAND
                or self.selected_future_command_set != [M063_GPU_VISIBILITY_COMMAND]
            ):
                raise ValueError("M063 runbook preview requires exact future command")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m063_gpu_visibility_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM063GPUVisibilityRunbookPreview:
    auth = load_lambda_m063_gpu_visibility_authorization(authorization)
    blockers = [*auth.blockers]
    if (
        auth.authorization_status
        != "authorized_for_future_m063_gpu_visibility_query_review"
    ):
        blockers.append("m063_authorization_not_ready")
    ready = not blockers
    return LambdaM063GPUVisibilityRunbookPreview(
        preview_status=(
            "ready_for_future_m063_gpu_visibility_query_review" if ready else "blocked"
        ),
        selected_command=(M063_GPU_VISIBILITY_COMMAND if ready else auth.selected_command),
        selected_future_command_set=auth.selected_future_command_set if ready else [],
        command_preview=[
            "M063 is a future supervised run; M062 does not execute this command.",
            "Launch exactly one approved instance, wait for SSH, run exactly:",
            M063_GPU_VISIBILITY_COMMAND,
            "Capture bounded stdout/stderr, terminate owned instance, verify termination.",
        ],
        blockers=sorted(set(blockers)),
        warnings=[
            "This runbook is non-executable",
            "M063 still requires immediate operator confirmation and one-shot arming",
        ],
    )


def load_lambda_m063_gpu_visibility_runbook_preview(
    path: str | Path,
) -> LambdaM063GPUVisibilityRunbookPreview:
    return LambdaM063GPUVisibilityRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m063_gpu_visibility_runbook_preview(
    path: str | Path,
    report: LambdaM063GPUVisibilityRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
