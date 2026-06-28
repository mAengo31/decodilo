"""Non-executable runbook preview for future M075R4 runtime-smoke retry."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    load_lambda_m075r4_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


class LambdaM075R4RuntimeSmokeRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    preview_status: str
    executable: bool = False
    authorization_status: str
    retry_same_runtime_smoke_command: bool
    declared_artifact_path: str = RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    capture_declared_artifact_on_success_or_failure: bool
    no_arbitrary_file_reads: bool = True
    no_training: bool = True
    no_downloads: bool = True
    runbook_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM075R4RuntimeSmokeRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("M075R4 runbook preview must remain non-executable")
        if self.billable_action_performed:
            raise ValueError("M075U runbook preview cannot spend money")
        if self.preview_status != "blocked" and self.blockers:
            raise ValueError("ready M075R4 preview cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r4_runtime_smoke_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM075R4RuntimeSmokeRunbookPreview:
    auth = load_lambda_m075r4_runtime_smoke_retry_authorization(authorization)
    blockers: list[str] = []
    if auth.authorization_status != "authorized_for_future_m075r4_runtime_smoke_retry":
        blockers.append("m075r4_authorization_not_valid")
    ready = not blockers
    return LambdaM075R4RuntimeSmokeRunbookPreview(
        preview_status=(
            "ready_for_future_m075r4_runtime_smoke_retry_review"
            if ready
            else "blocked"
        ),
        authorization_status=auth.authorization_status,
        retry_same_runtime_smoke_command=True,
        capture_declared_artifact_on_success_or_failure=True,
        runbook_steps=[
            "fresh read-only discovery",
            "one launch only after explicit operator confirmation",
            "wait for TCP/22 and SSH banner readiness before upload",
            "upload source and dependency bundles once",
            "install dependencies from local wheelhouse only",
            "run the exact runtime-smoke command once",
            "capture only the declared runtime-smoke artifact on success or failure",
            "terminate owned instance and verify clean discovery",
        ],
        blockers=sorted(set(blockers)),
        warnings=["preview is non-executable and future-only"],
    )


def load_lambda_m075r4_runtime_smoke_runbook_preview(
    path: str | Path,
) -> LambdaM075R4RuntimeSmokeRunbookPreview:
    return LambdaM075R4RuntimeSmokeRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r4_runtime_smoke_runbook_preview(
    path: str | Path,
    preview: LambdaM075R4RuntimeSmokeRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(preview.to_json(), encoding="utf-8")
