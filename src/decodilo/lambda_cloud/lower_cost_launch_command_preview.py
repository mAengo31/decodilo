"""Non-executable command preview for a future lower-cost M039 run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    LambdaLowerCostM039Authorization,
    load_lambda_lower_cost_m039_authorization,
)

LambdaLowerCostCommandPreviewStatus = Literal[
    "ready_for_future_m039",
    "ready_for_future_review",
    "blocked",
]


class LambdaLowerCostLaunchCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaLowerCostCommandPreviewStatus
    executable: bool = False
    workdir: str = "/tmp/decodilo-lambda-m039"
    selected_shape: str = "gpu_1x_h100_pcie"
    selected_ssh_key_hash: str | None = None
    response_loss_controls_ref: str = "/tmp/decodilo-lambda-strand-response-loss-controls.json"
    command: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaLowerCostLaunchCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost command preview must remain non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_launch_command_preview(
    *,
    authorization: LambdaLowerCostM039Authorization,
) -> LambdaLowerCostLaunchCommandPreview:
    blocked = bool(authorization.blockers)
    command = [
        "python",
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--env-file",
        ".env",
        "--env-key",
        "LAMBDA_API_KEY",
        "--m039-authorization",
        "/tmp/decodilo-lambda-m039-authorization.json",
        "--lower-cost-canonical-readiness",
        "/tmp/decodilo-lambda-lower-cost-canonical-readiness.json",
        "--lower-cost-state-snapshot",
        "/tmp/decodilo-lambda-lower-cost-state-snapshot.json",
        "--lower-cost-budget-lock",
        "/tmp/decodilo-lambda-lower-cost-budget-lock.json",
        "--lower-cost-resource-lock",
        "/tmp/decodilo-lambda-lower-cost-resource-lock.json",
        "--lower-cost-launch-window-lock",
        "/tmp/decodilo-lambda-lower-cost-launch-window-lock.json",
        "--lower-cost-launch-plan",
        "/tmp/decodilo-lambda-strand-lower-cost-plan.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--lower-cost-gate-check",
        "/tmp/decodilo-lambda-lower-cost-gate-check.json",
        "--m038a-report",
        "/tmp/decodilo-lambda-m038a-report.json",
        "--workdir",
        "/tmp/decodilo-lambda-m039",
        "--execute-real-launch",
        "<future-operator-confirmation-required>",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
    ]
    return LambdaLowerCostLaunchCommandPreview(
        preview_status="blocked" if blocked else "ready_for_future_m039",
        selected_shape=authorization.selected_shape,
        selected_ssh_key_hash=authorization.selected_ssh_key_hash,
        command=command,
        blockers=authorization.blockers,
        warnings=[
            "command preview is non-executable in M038",
            "future M039 must re-run gates and collect operator confirmation",
        ],
    )


def build_lambda_lower_cost_launch_command_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaLowerCostLaunchCommandPreview:
    return build_lambda_lower_cost_launch_command_preview(
        authorization=load_lambda_lower_cost_m039_authorization(authorization)
    )


def load_lambda_lower_cost_launch_command_preview(
    path: str | Path,
) -> LambdaLowerCostLaunchCommandPreview:
    return LambdaLowerCostLaunchCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_launch_command_preview(
    path: str | Path,
    report: LambdaLowerCostLaunchCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
