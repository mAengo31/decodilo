"""Non-executable command preview for future M046 capacity-selected review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_gate_check import (
    load_lambda_capacity_selected_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)

LambdaCapacitySelectedCommandPreviewStatus = Literal[
    "ready_for_future_m046_capacity_selected_review",
    "blocked",
]


class LambdaCapacitySelectedCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaCapacitySelectedCommandPreviewStatus
    executable: bool = False
    selected_candidate: str | None = None
    command_preview: list[str] = Field(default_factory=list)
    raw_ssh_key_name_present: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaCapacitySelectedCommandPreview:
        if (
            self.executable
            or self.raw_ssh_key_name_present
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-selected command preview cannot execute launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_selected_command_preview_from_paths(
    *,
    authorization: str | Path,
    gate_check: str | Path,
) -> LambdaCapacitySelectedCommandPreview:
    auth = load_lambda_capacity_selected_m046_authorization(authorization)
    gate = load_lambda_capacity_selected_gate_check(gate_check)
    blockers = [*auth.blockers, *gate.blockers]
    if not gate.gate_passed:
        blockers.append("capacity_selected_gate_not_passed")
    ready = (
        auth.authorization_status
        == "authorized_for_future_m046_capacity_selected_launch_review"
        and not blockers
    )
    return LambdaCapacitySelectedCommandPreview(
        preview_status=(
            "ready_for_future_m046_capacity_selected_review" if ready else "blocked"
        ),
        selected_candidate=auth.selected_candidate if ready else None,
        command_preview=_command_preview() if ready else [],
        blockers=sorted(set(blockers)),
        warnings=[
            "command preview is non-executable",
            "raw SSH key names are not included in public preview artifacts",
        ],
    )


def _command_preview() -> list[str]:
    return [
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
        "--capacity-selected-m046-authorization",
        "/tmp/decodilo-lambda-m046-authorization.json",
        "--capacity-selected-cost-risk-review",
        "/tmp/decodilo-lambda-capacity-selected-cost-risk-review.json",
        "--capacity-selected-operator-approval",
        "/tmp/decodilo-lambda-capacity-selected-operator-approval.json",
        "--capacity-selected-gate-check",
        "/tmp/decodilo-lambda-capacity-selected-gate-check.json",
        "--capacity-aware-selector-output",
        "/tmp/decodilo-lambda-capacity-aware-flex-selector.json",
        "--capacity-aware-selector-authorization",
        "/tmp/decodilo-lambda-capacity-aware-flex-authorization.json",
        "--capacity-aware-selector-gate-check",
        "/tmp/decodilo-lambda-capacity-aware-flex-gate-check.json",
        "--capacity-history",
        "/tmp/decodilo-lambda-capacity-history.json",
        "--capacity-retry-policy",
        "/tmp/decodilo-lambda-capacity-retry-policy.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--m045-report",
        "/tmp/decodilo-lambda-m045-report.json",
        "--workdir",
        "/tmp/decodilo-lambda-m046",
        "--execute-real-launch",
        "--confirm-billable-action",
        "<exact billable-action confirmation>",
        "--confirm-terminate-required",
        "<exact terminate-required confirmation>",
    ]


def load_lambda_capacity_selected_command_preview(
    path: str | Path,
) -> LambdaCapacitySelectedCommandPreview:
    return LambdaCapacitySelectedCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_command_preview(
    path: str | Path,
    report: LambdaCapacitySelectedCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
