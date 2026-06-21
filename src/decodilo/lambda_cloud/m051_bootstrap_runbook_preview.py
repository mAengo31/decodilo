"""Non-executable runbook preview for a future M051 Lambda bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    load_lambda_m051_bootstrap_authorization,
)

LambdaM051BootstrapRunbookPreviewStatus = Literal[
    "ready_for_future_m051_bootstrap_review",
    "blocked",
]


class LambdaM051BootstrapRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaM051BootstrapRunbookPreviewStatus
    executable: bool = False
    selected_bootstrap_mode: str | None = None
    ssh_approval_required_before_ssh: bool = True
    command_approval_required_before_remote_command: bool = True
    package_install_allowed: bool = False
    training_allowed: bool = False
    runbook_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaM051BootstrapRunbookPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.package_install_allowed
            or self.training_allowed
        ):
            raise ValueError("M051 runbook preview cannot execute or enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_bootstrap_runbook_preview_from_paths(
    *,
    authorization: str | Path,
) -> LambdaM051BootstrapRunbookPreview:
    auth = load_lambda_m051_bootstrap_authorization(authorization)
    ready = auth.authorization_status != "not_authorized" and not auth.blockers
    return LambdaM051BootstrapRunbookPreview(
        preview_status="ready_for_future_m051_bootstrap_review"
        if ready
        else "blocked",
        selected_bootstrap_mode=auth.selected_bootstrap_mode if ready else None,
        runbook_steps=_runbook_steps(auth.selected_bootstrap_mode) if ready else [],
        blockers=auth.blockers,
        warnings=[
            "runbook preview is non-executable",
            "future M051 still requires immediate operator confirmation",
            "owned instance termination and read-only verification remain mandatory",
        ],
    )


def _runbook_steps(mode: str | None) -> list[str]:
    steps = [
        "Verify M050 authorization artifacts and launch-disabled flags.",
        "Run fresh pre-launch safety gates in the future M051 milestone.",
        "Launch exactly one approved Lambda instance if all future gates pass.",
        "Verify the owned instance through Lambda read-only get/list.",
    ]
    if mode == "lifecycle_plus_metadata_only":
        steps.append("Collect provider/local metadata only; do not SSH.")
    elif mode == "lifecycle_plus_ssh_connectivity_check":
        steps.append("Open only an approved SSH connectivity check; run no command.")
    elif mode == "lifecycle_plus_single_benign_command":
        steps.append("Run only the approved single allowlisted command.")
    steps.extend(
        [
            "Do not install packages, run setup scripts, use cloud-init, or train.",
            "Terminate exactly the owned instance in the same supervised run.",
            "Verify terminal or absent state through Lambda read-only discovery/list/get.",
        ]
    )
    return steps


def load_lambda_m051_bootstrap_runbook_preview(
    path: str | Path,
) -> LambdaM051BootstrapRunbookPreview:
    return LambdaM051BootstrapRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_bootstrap_runbook_preview(
    path: str | Path,
    report: LambdaM051BootstrapRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
