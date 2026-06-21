"""Non-executable command preview for capacity-history-aware selector review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)
from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    load_lambda_capacity_history_selector_gate_check,
)

LambdaCapacityHistorySelectorCommandPreviewStatus = Literal[
    "ready_for_future_capacity_history_selector_review",
    "blocked",
]


class LambdaCapacityHistorySelectorCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaCapacityHistorySelectorCommandPreviewStatus
    executable: bool = False
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    command_preview: list[str] = Field(default_factory=list)
    hardcoded_shape_outside_selector_output: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaCapacityHistorySelectorCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.hardcoded_shape_outside_selector_output
        ):
            raise ValueError("capacity-history selector preview cannot execute launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_history_selector_command_preview_from_paths(
    *,
    authorization: str | Path,
    gate_check: str | Path,
) -> LambdaCapacityHistorySelectorCommandPreview:
    auth = load_lambda_capacity_history_selector_authorization(authorization)
    gate = load_lambda_capacity_history_selector_gate_check(gate_check)
    blockers = [*auth.blockers, *gate.blockers]
    if not gate.gate_passed:
        blockers.append("capacity_history_selector_gate_not_passed")
    ready = (
        auth.authorization_status
        == "authorized_for_future_capacity_history_selector_review"
        and not blockers
    )
    return LambdaCapacityHistorySelectorCommandPreview(
        preview_status=(
            "ready_for_future_capacity_history_selector_review" if ready else "blocked"
        ),
        selected_candidate=auth.selected_candidate if ready else None,
        selected_candidate_source=auth.selected_candidate_source if ready else None,
        command_preview=_command_preview() if ready else [],
        blockers=sorted(set(blockers)),
        warnings=[
            "command preview is non-executable",
            "selected shape is supplied by capacity-aware selector artifacts",
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
        "--capacity-history-selector-authorization",
        "/tmp/decodilo-lambda-capacity-aware-flex-authorization.json",
        "--capacity-history-selector-output",
        "/tmp/decodilo-lambda-capacity-aware-flex-selector.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--workdir",
        "/tmp/decodilo-lambda-capacity-aware-flex",
    ]


def load_lambda_capacity_history_selector_command_preview(
    path: str | Path,
) -> LambdaCapacityHistorySelectorCommandPreview:
    return LambdaCapacityHistorySelectorCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history_selector_command_preview(
    path: str | Path,
    report: LambdaCapacityHistorySelectorCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
