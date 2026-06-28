"""Non-executable runbook preview for future M065 Python runtime query."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m065_python_runtime_authorization import (
    load_lambda_m065_python_runtime_authorization,
)

LambdaM065PythonRuntimeRunbookPreviewStatus = Literal[
    "ready_for_future_m065_python_version_query_review",
    "blocked",
]


class LambdaM065PythonRuntimeRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaM065PythonRuntimeRunbookPreviewStatus
    executable: bool = False
    selected_future_command_set: list[str] = Field(default_factory=list)
    selected_command: str | None = None
    runbook_steps: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaM065PythonRuntimeRunbookPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M065 runbook preview must remain non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m065_python_runtime_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM065PythonRuntimeRunbookPreview:
    auth = load_lambda_m065_python_runtime_authorization(authorization)
    blockers = [*auth.blockers]
    if auth.authorization_status != "authorized_for_future_m065_python_version_query_review":
        blockers.append("m065_python_runtime_authorization_not_ready")
    status: LambdaM065PythonRuntimeRunbookPreviewStatus = (
        "ready_for_future_m065_python_version_query_review"
        if not blockers
        else "blocked"
    )
    return LambdaM065PythonRuntimeRunbookPreview(
        preview_status=status,
        selected_future_command_set=auth.selected_future_command_set,
        selected_command=auth.selected_command,
        runbook_steps=[
            "Run fresh read-only Lambda discovery before any future launch.",
            "Launch at most one approved instance in a supervised M065 milestone.",
            "Attempt SSH only for the approved exact remote command.",
            "Run exactly: python3 --version.",
            "Capture bounded stdout/stderr and redact secrets.",
            (
                "Do not run Python scripts, inline Python, imports, pip, package "
                "installs, training, transfers, or port forwards."
            ),
            (
                "Terminate the owned instance and verify termination through Lambda "
                "read-only discovery/list/get."
            ),
        ],
        blockers=sorted(set(blockers)),
        warnings=[
            "M065 runbook preview is non-executable",
            "M064 does not authorize immediate launch or command execution",
        ],
    )


def load_lambda_m065_python_runtime_runbook_preview(
    path: str | Path,
) -> LambdaM065PythonRuntimeRunbookPreview:
    return LambdaM065PythonRuntimeRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m065_python_runtime_runbook_preview(
    path: str | Path,
    report: LambdaM065PythonRuntimeRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
