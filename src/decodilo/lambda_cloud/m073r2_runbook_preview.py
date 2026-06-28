"""Non-executable M073R2 retry runbook preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m073r2_retry_authorization import (
    load_lambda_m073r2_retry_authorization,
)
from decodilo.lambda_cloud.source_bundle_upload_policy import (
    load_lambda_source_dependency_upload_policy,
)

LambdaM073R2RunbookPreviewStatus = Literal[
    "ready_for_future_m073r2_tiny_smoke_retry_review",
    "blocked",
]


class LambdaM073R2RunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    preview_status: LambdaM073R2RunbookPreviewStatus
    executable: bool = False
    required_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM073R2RunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("M073R2 runbook preview must be non-executable")
        if self.billable_action_performed:
            raise ValueError("M073S runbook preview cannot spend money")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m073r2_runbook_preview_from_paths(
    *,
    authorization: str | Path,
    upload_policy: str | Path,
) -> LambdaM073R2RunbookPreview:
    auth = load_lambda_m073r2_retry_authorization(authorization)
    policy = load_lambda_source_dependency_upload_policy(upload_policy)
    ready = (
        auth.authorization_status == "authorized_for_future_m073r2_tiny_smoke_retry"
        and policy.upload_policy_status == "policy_defined"
    )
    blockers = list(auth.blockers)
    if policy.upload_policy_status != "policy_defined":
        blockers.append("upload_policy_not_defined")
    return LambdaM073R2RunbookPreview(
        preview_status=(
            "ready_for_future_m073r2_tiny_smoke_retry_review" if ready else "blocked"
        ),
        required_steps=[
            "fresh read-only discovery confirms gpu_1x_a10/us-east-1 availability",
            "exactly one launch attempt",
            "host discovery",
            "TCP/22 readiness",
            "SSH banner readiness before upload",
            "exactly one source bundle upload",
            "source hash verification before dependency upload",
            "exactly one dependency bundle upload",
            "dependency hash verification before extraction/install",
            "local-only dependency install",
            "exact tiny-smoke command",
            "terminate owned instance and verify through read-only discovery/list/get",
        ],
        blockers=blockers,
        warnings=["M073S does not execute this runbook preview"],
    )


def load_lambda_m073r2_runbook_preview(path: str | Path) -> LambdaM073R2RunbookPreview:
    return LambdaM073R2RunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m073r2_runbook_preview(
    path: str | Path,
    report: LambdaM073R2RunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
