"""Non-executable M093R tiny real-training smoke runbook preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m093r_tiny_real_training_authorization import (
    load_lambda_m093r_tiny_real_training_authorization,
)

LambdaM093RTinyRealTrainingRunbookPreviewStatus = Literal[
    "ready_for_future_m093r_tiny_real_training_review",
    "blocked_no_safe_tiny_real_training_command",
    "blocked",
]


class LambdaM093RTinyRealTrainingRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    preview_status: LambdaM093RTinyRealTrainingRunbookPreviewStatus
    executable: bool = False
    workdir_placeholder: str = "/tmp/decodilo-lambda-m093r"
    future_requirements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM093RTinyRealTrainingRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("M093R runbook preview must be non-executable")
        if self.billable_action_performed:
            raise ValueError("M092 runbook preview cannot spend money")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m093r_tiny_real_training_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM093RTinyRealTrainingRunbookPreview:
    auth = load_lambda_m093r_tiny_real_training_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m093r_tiny_real_training_smoke"
    )
    if ready:
        status: LambdaM093RTinyRealTrainingRunbookPreviewStatus = (
            "ready_for_future_m093r_tiny_real_training_review"
        )
    elif "tiny_real_training_smoke_not_verified" in auth.blockers:
        status = "blocked_no_safe_tiny_real_training_command"
    else:
        status = "blocked"
    return LambdaM093RTinyRealTrainingRunbookPreview(
        preview_status=status,
        future_requirements=[
            "fresh read-only discovery must confirm approved candidate availability",
            "exactly one launch attempt and one owned termination",
            "upload exactly source bundle and dependency bundle",
            "install dependencies from uploaded local wheelhouse only with --no-index",
            "run one tiny-real-training-smoke command",
            "capture only /tmp/decodilo-tiny-real-training-smoke.json",
            "artifact must truthfully claim only tiny real training mechanics",
            "terminate owned instance and verify through read-only discovery/list/get",
        ],
        blockers=auth.blockers,
        warnings=["M092 does not execute this runbook preview"],
    )


def load_lambda_m093r_tiny_real_training_runbook_preview(
    path: str | Path,
) -> LambdaM093RTinyRealTrainingRunbookPreview:
    return LambdaM093RTinyRealTrainingRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m093r_tiny_real_training_runbook_preview(
    path: str | Path,
    report: LambdaM093RTinyRealTrainingRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
