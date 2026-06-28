"""Future-only retry decision for remote vertical-slice runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vslice_candidate_selector import (
    load_lambda_remote_vslice_candidate_selection,
)

LambdaRemoteVSliceRetryDecisionStatus = Literal[
    "wait_for_ssh_proven_candidate_live",
    "authorize_future_m067r2_on_ssh_proven_candidate",
    "require_operator_approval_for_new_candidate_exploration",
    "pause_remote_vslice",
]


class LambdaRemoteVSliceRetryDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaRemoteVSliceRetryDecisionStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    decision_authorizes_future_review_only: bool = True
    immediate_launch_authorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteVSliceRetryDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.immediate_launch_authorized
        ):
            raise ValueError("M067S retry decision cannot authorize immediate launch")
        if self.decision_status == "authorize_future_m067r2_on_ssh_proven_candidate" and (
            not self.selected_candidate or not self.selected_region
        ):
            raise ValueError("future M067R2 authorization decision requires a candidate")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vslice_retry_decision_from_path(
    *,
    candidate_selection: str | Path,
) -> LambdaRemoteVSliceRetryDecision:
    selection = load_lambda_remote_vslice_candidate_selection(candidate_selection)
    if selection.selection_status == "selected_ssh_proven_candidate":
        return LambdaRemoteVSliceRetryDecision(
            decision_status="authorize_future_m067r2_on_ssh_proven_candidate",
            selected_candidate=selection.selected_candidate,
            selected_region=selection.selected_region,
            warnings=[
                "Authorization is future-only and still requires fresh live gates before launch",
            ],
        )
    if selection.selection_status == "requires_fresh_readonly_discovery":
        return LambdaRemoteVSliceRetryDecision(
            decision_status="wait_for_ssh_proven_candidate_live",
            blockers=["fresh_readonly_discovery_required_before_future_m067r2"],
            warnings=[
                "M067S performs no live discovery; wait for fresh evidence before retry",
            ],
        )
    if selection.selection_status == "known_ssh_ready_candidate_not_live":
        return LambdaRemoteVSliceRetryDecision(
            decision_status="wait_for_ssh_proven_candidate_live",
            blockers=["known_ssh_ready_candidate_not_live"],
        )
    if selection.selection_status == "require_operator_approval_for_new_candidate_exploration":
        return LambdaRemoteVSliceRetryDecision(
            decision_status="require_operator_approval_for_new_candidate_exploration",
            blockers=["operator_approval_required_for_new_candidate_exploration"],
        )
    return LambdaRemoteVSliceRetryDecision(
        decision_status="pause_remote_vslice",
        blockers=["no_safe_remote_vslice_candidate"],
    )


def load_lambda_remote_vslice_retry_decision(
    path: str | Path,
) -> LambdaRemoteVSliceRetryDecision:
    return LambdaRemoteVSliceRetryDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vslice_retry_decision(
    path: str | Path,
    report: LambdaRemoteVSliceRetryDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
