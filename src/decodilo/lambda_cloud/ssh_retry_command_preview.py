"""Non-executable preview for a future M056 SSH retry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    load_lambda_ssh_retry_future_authorization,
)

LambdaSSHRetryCommandPreviewStatus = Literal[
    "ready_for_future_m056_live_candidate_ssh_retry_review",
    "blocked",
]


class LambdaSSHRetryCommandPreviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaSSHRetryCommandPreviewStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    executable: bool = False
    command_preview: list[str] = Field(default_factory=list)
    includes_redacted_stderr_capture_policy: bool = True
    no_remote_command: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHRetryCommandPreviewReport:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M056 command preview must remain non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_retry_command_preview_from_path(
    authorization: str | Path,
) -> LambdaSSHRetryCommandPreviewReport:
    auth = load_lambda_ssh_retry_future_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m056_live_candidate_ssh_retry_review"
    )
    command = [
        "python",
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        "/tmp/decodilo-lambda-m056",
        "--execute-real-launch",
        "--m056-live-candidate-selection",
        "/tmp/decodilo-lambda-ssh-live-candidate-selection.json",
        "--m056-authorization",
        "/tmp/decodilo-lambda-m056-ssh-retry-authorization.json",
        "--ssh-stderr-capture-policy",
        "/tmp/decodilo-lambda-ssh-stderr-capture-policy.json",
        "--confirm-billable-action",
        "<operator confirmation required>",
        "--confirm-terminate-required",
        "<operator confirmation required>",
    ]
    return LambdaSSHRetryCommandPreviewReport(
        preview_status=(
            "ready_for_future_m056_live_candidate_ssh_retry_review"
            if ready
            else "blocked"
        ),
        selected_candidate=auth.selected_candidate,
        selected_region=auth.selected_region,
        command_preview=command if ready else [],
        blockers=auth.blockers,
        warnings=[
            "M055D does not execute this command",
            "future M056 must regenerate one-shot gates and fresh read-only discovery",
        ],
    )


def load_lambda_ssh_retry_command_preview(
    path: str | Path,
) -> LambdaSSHRetryCommandPreviewReport:
    return LambdaSSHRetryCommandPreviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_retry_command_preview(
    path: str | Path,
    report: LambdaSSHRetryCommandPreviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
