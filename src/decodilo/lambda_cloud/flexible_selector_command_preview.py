"""Non-executable command preview for future flexible-selector launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.flexible_selector_authorization import (
    load_lambda_flexible_selector_authorization,
)
from decodilo.lambda_cloud.flexible_selector_fixed_shape_audit import (
    load_lambda_flexible_selector_fixed_shape_audit,
)
from decodilo.lambda_cloud.flexible_selector_gate_check import (
    load_lambda_flexible_selector_gate_check,
)

LambdaFlexibleSelectorCommandPreviewStatus = Literal[
    "ready_for_future_flexible_selector_review",
    "blocked",
]


class LambdaFlexibleSelectorCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaFlexibleSelectorCommandPreviewStatus
    executable: bool = False
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_ssh_key_hash: str | None = None
    workdir_placeholder: str = "/tmp/decodilo-lambda-flex"
    command_preview: list[str] = Field(default_factory=list)
    includes_raw_ssh_key_name: bool = False
    hardcoded_shape_outside_selector_output: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaFlexibleSelectorCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.includes_raw_ssh_key_name
            or self.hardcoded_shape_outside_selector_output
        ):
            raise ValueError("flexible-selector command preview cannot execute launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_flexible_selector_command_preview_from_paths(
    *,
    authorization: str | Path,
    gate_check: str | Path,
    fixed_shape_audit: str | Path,
) -> LambdaFlexibleSelectorCommandPreview:
    auth = load_lambda_flexible_selector_authorization(authorization)
    gate = load_lambda_flexible_selector_gate_check(gate_check)
    audit = load_lambda_flexible_selector_fixed_shape_audit(fixed_shape_audit)
    blockers = [*auth.blockers, *gate.blockers, *audit.blockers]
    if not gate.gate_passed:
        blockers.append("flexible_selector_gate_not_passed")
    if not audit.audit_passed:
        blockers.append("fixed_shape_audit_not_passed")
    ready = (
        auth.authorization_status == "authorized_for_future_flexible_selector_launch_review"
        and not blockers
    )
    return LambdaFlexibleSelectorCommandPreview(
        preview_status=(
            "ready_for_future_flexible_selector_review" if ready else "blocked"
        ),
        selected_candidate=auth.selected_candidate if ready else None,
        selected_candidate_source=auth.selected_candidate_source if ready else None,
        selected_ssh_key_hash=auth.selected_ssh_key_hash if ready else None,
        command_preview=_command_preview() if ready else [],
        blockers=sorted(set(blockers)),
        warnings=[
            "command preview is non-executable",
            "raw SSH key names are not included in the preview",
            "selected shape is supplied by selector artifacts at execution time",
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
        "--flexible-selector-authorization",
        "/tmp/decodilo-lambda-flex-selector-authorization.json",
        "--flexible-selector-output",
        "/tmp/decodilo-lambda-flex-selector-risk-accepted.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--workdir",
        "/tmp/decodilo-lambda-flex",
        "--execute-real-launch",
        "--confirm-billable-action",
        "I understand this may create a billable Lambda instance and must be terminated",
        "--confirm-terminate-required",
        "I understand this run must terminate the owned instance and verify termination",
    ]


def load_lambda_flexible_selector_command_preview(
    path: str | Path,
) -> LambdaFlexibleSelectorCommandPreview:
    return LambdaFlexibleSelectorCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_flexible_selector_command_preview(
    path: str | Path,
    report: LambdaFlexibleSelectorCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
