"""Non-executable M075R2 runtime-smoke retry runbook preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    load_lambda_m075r2_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    load_lambda_remote_vslice_failure_artifact_capture_policy,
)

LambdaM075R2RuntimeSmokeRunbookPreviewStatus = Literal[
    "ready_for_future_m075r2_runtime_smoke_retry_review",
    "blocked",
]


class LambdaM075R2RuntimeSmokeRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    preview_status: LambdaM075R2RuntimeSmokeRunbookPreviewStatus
    executable: bool = False
    required_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM075R2RuntimeSmokeRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("M075R2 runbook preview must be non-executable")
        if self.billable_action_performed:
            raise ValueError("M075S runbook preview cannot spend money")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r2_runtime_smoke_runbook_preview_from_paths(
    *,
    authorization: str | Path,
    failure_artifact_policy: str | Path,
) -> LambdaM075R2RuntimeSmokeRunbookPreview:
    auth = load_lambda_m075r2_runtime_smoke_retry_authorization(authorization)
    capture = load_lambda_remote_vslice_failure_artifact_capture_policy(
        failure_artifact_policy
    )
    ready = (
        auth.authorization_status == "authorized_for_future_m075r2_runtime_smoke_retry"
        and capture.policy_passed
    )
    blockers = list(auth.blockers)
    if not capture.policy_passed:
        blockers.extend(capture.blockers or ["failure_artifact_capture_policy_failed"])
    return LambdaM075R2RuntimeSmokeRunbookPreview(
        preview_status=(
            "ready_for_future_m075r2_runtime_smoke_retry_review" if ready else "blocked"
        ),
        required_steps=[
            "fresh read-only discovery confirms gpu_1x_a10/us-east-1 availability",
            "exactly one launch attempt",
            "TCP/22 and SSH banner readiness before upload",
            "exactly one source bundle upload",
            "exactly one dependency bundle upload",
            "local-only dependency install",
            "exact runtime-smoke command",
            "capture /tmp/decodilo-runtime-smoke.json metadata on success or failure",
            "no arbitrary file reads",
            "terminate owned instance and verify through read-only discovery/list/get",
        ],
        blockers=sorted(set(blockers)),
        warnings=["M075S does not execute this runbook preview"],
    )


def load_lambda_m075r2_runtime_smoke_runbook_preview(
    path: str | Path,
) -> LambdaM075R2RuntimeSmokeRunbookPreview:
    return LambdaM075R2RuntimeSmokeRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r2_runtime_smoke_runbook_preview(
    path: str | Path,
    report: LambdaM075R2RuntimeSmokeRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
