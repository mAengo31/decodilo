"""Non-executable M089R bounded synthetic DiLoCo experiment runbook preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    load_lambda_m089r_bounded_diloco_experiment_authorization,
)

LambdaM089RBoundedDilocoExperimentRunbookPreviewStatus = Literal[
    "ready_for_future_m089r_bounded_diloco_experiment_review",
    "blocked_no_safe_bounded_diloco_experiment_command",
    "blocked",
]


class LambdaM089RBoundedDilocoExperimentRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    preview_status: LambdaM089RBoundedDilocoExperimentRunbookPreviewStatus
    executable: bool = False
    workdir_placeholder: str = "/tmp/decodilo-lambda-m089r"
    future_requirements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM089RBoundedDilocoExperimentRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("runbook preview must be non-executable and disabled")
        if self.billable_action_performed:
            raise ValueError("M088 runbook preview cannot spend money")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM089RBoundedDilocoExperimentRunbookPreview:
    auth = load_lambda_m089r_bounded_diloco_experiment_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m089r_bounded_diloco_experiment"
    )
    if ready:
        status: LambdaM089RBoundedDilocoExperimentRunbookPreviewStatus = (
            "ready_for_future_m089r_bounded_diloco_experiment_review"
        )
    elif "no_safe_bounded_diloco_experiment_command_found" in auth.blockers:
        status = "blocked_no_safe_bounded_diloco_experiment_command"
    else:
        status = "blocked"
    return LambdaM089RBoundedDilocoExperimentRunbookPreview(
        preview_status=status,
        future_requirements=[
            "fresh read-only discovery must confirm approved candidate availability",
            "exactly one launch attempt and one owned termination",
            "upload exactly source bundle and dependency bundle",
            "install dependencies from uploaded local wheelhouse only with --no-index",
            "run one complete bounded synthetic DiLoCo experiment command",
            "artifact must combine protocol, optimizer, synthetic fragments, "
            "and replay/metric checks",
            "terminate owned instance and verify through read-only discovery/list/get",
        ],
        blockers=auth.blockers,
        warnings=["M088 does not execute this runbook preview"],
    )


def load_lambda_m089r_bounded_diloco_experiment_runbook_preview(
    path: str | Path,
) -> LambdaM089RBoundedDilocoExperimentRunbookPreview:
    return LambdaM089RBoundedDilocoExperimentRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m089r_bounded_diloco_experiment_runbook_preview(
    path: str | Path,
    report: LambdaM089RBoundedDilocoExperimentRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
