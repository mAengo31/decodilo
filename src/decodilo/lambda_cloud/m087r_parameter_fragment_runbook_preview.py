"""Non-executable M087R parameter-fragment synthetic runbook preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    load_lambda_m087r_parameter_fragment_authorization,
)

LambdaM087RParameterFragmentRunbookPreviewStatus = Literal[
    "ready_for_future_m087r_parameter_fragment_review",
    "blocked_no_safe_parameter_fragment_command",
    "blocked",
]


class LambdaM087RParameterFragmentRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086A"
    preview_status: LambdaM087RParameterFragmentRunbookPreviewStatus
    executable: bool = False
    workdir_placeholder: str = "/tmp/decodilo-lambda-m087r"
    future_requirements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM087RParameterFragmentRunbookPreview:
        if self.executable or self.launch_ready or self.launch_allowed:
            raise ValueError("runbook preview must be non-executable and disabled")
        if self.billable_action_performed:
            raise ValueError("M086 runbook preview cannot spend money")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m087r_parameter_fragment_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM087RParameterFragmentRunbookPreview:
    auth = load_lambda_m087r_parameter_fragment_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m087r_parameter_fragment_smoke"
    )
    if ready:
        status: LambdaM087RParameterFragmentRunbookPreviewStatus = (
            "ready_for_future_m087r_parameter_fragment_review"
        )
    elif "no_safe_parameter_fragment_command_found" in auth.blockers:
        status = "blocked_no_safe_parameter_fragment_command"
    else:
        status = "blocked"
    return LambdaM087RParameterFragmentRunbookPreview(
        preview_status=status,
        future_requirements=[
            "fresh read-only discovery must confirm approved candidate availability",
            "exactly one launch attempt and one owned termination",
            "upload exactly source bundle and dependency bundle",
            "install dependencies from uploaded local wheelhouse only with --no-index",
            "run exactly one bounded parameter-fragment synthetic command",
            "artifact must prove synthetic_vector_fragments without training, overlap, "
            "or quantization claims unless active",
            "terminate owned instance and verify through read-only discovery/list/get",
        ],
        blockers=auth.blockers,
        warnings=["M086A does not execute this runbook preview"],
    )


def load_lambda_m087r_parameter_fragment_runbook_preview(
    path: str | Path,
) -> LambdaM087RParameterFragmentRunbookPreview:
    return LambdaM087RParameterFragmentRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m087r_parameter_fragment_runbook_preview(
    path: str | Path,
    report: LambdaM087RParameterFragmentRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
