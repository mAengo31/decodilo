"""Future-only M067R2 authorization record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vslice_retry_decision import (
    load_lambda_remote_vslice_retry_decision,
)

LambdaRemoteVSliceRetryAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m067r2_ssh_proven_candidate_review",
]


class LambdaRemoteVSliceRetryAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaRemoteVSliceRetryAuthorizationStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    future_review_only: bool = True
    launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteVSliceRetryAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
        ):
            raise ValueError("M067R2 authorization cannot authorize immediate launch")
        if (
            self.authorization_status
            == "authorized_for_future_m067r2_ssh_proven_candidate_review"
            and (not self.selected_candidate or not self.selected_region or self.blockers)
        ):
            raise ValueError("future M067R2 authorization requires candidate and no blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vslice_retry_authorization_from_path(
    *,
    decision: str | Path,
) -> LambdaRemoteVSliceRetryAuthorization:
    retry = load_lambda_remote_vslice_retry_decision(decision)
    if retry.decision_status == "authorize_future_m067r2_on_ssh_proven_candidate":
        return LambdaRemoteVSliceRetryAuthorization(
            authorization_status="authorized_for_future_m067r2_ssh_proven_candidate_review",
            selected_candidate=retry.selected_candidate,
            selected_region=retry.selected_region,
            warnings=[
                "M067R2 authorization is future-only and cannot send a request now",
            ],
        )
    return LambdaRemoteVSliceRetryAuthorization(
        authorization_status="not_authorized",
        blockers=retry.blockers or [retry.decision_status],
        warnings=[
            "M067S does not authorize immediate launch",
        ],
    )


def load_lambda_remote_vslice_retry_authorization(
    path: str | Path,
) -> LambdaRemoteVSliceRetryAuthorization:
    return LambdaRemoteVSliceRetryAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_retry_authorization(
    path: str | Path,
    report: LambdaRemoteVSliceRetryAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
