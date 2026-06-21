"""M045 decision record for capacity-selected future launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    load_lambda_capacity_selected_operator_approval,
)

LambdaM045DecisionStatus = Literal[
    "authorize_future_m046_capacity_selected_launch_review",
    "wait_for_live_availability",
    "require_manual_candidate_selection",
    "needs_more_evidence",
]


class LambdaM045DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaM045DecisionStatus
    selected_candidate: str | None = None
    future_review_allowed: bool = False
    launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM045DecisionRecord:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M045 decision cannot authorize immediate launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m045_decision_record_from_paths(
    *,
    operator_approval: str | Path,
    authorization: str | Path | None = None,
) -> LambdaM045DecisionRecord:
    approval = load_lambda_capacity_selected_operator_approval(operator_approval)
    auth = (
        None
        if authorization is None or not Path(authorization).exists()
        else load_lambda_capacity_selected_m046_authorization(authorization)
    )
    blockers = list(approval.blockers)
    selected = None
    future_allowed = False
    if approval.approval_status == "declined_wait_for_live_availability":
        status: LambdaM045DecisionStatus = "wait_for_live_availability"
    elif approval.approval_status == "declined_manual_candidate_selection":
        status = "require_manual_candidate_selection"
    elif (
        approval.approval_status
        == "approved_for_future_m046_capacity_selected_launch_review"
    ):
        if (
            auth is not None
            and auth.authorization_status
            == "authorized_for_future_m046_capacity_selected_launch_review"
            and not auth.blockers
        ):
            status = "authorize_future_m046_capacity_selected_launch_review"
            selected = auth.selected_candidate
            future_allowed = True
        else:
            status = "needs_more_evidence"
            blockers.extend(
                ["m046_authorization_missing_or_not_ready"]
                if auth is None
                else auth.blockers
            )
    else:
        status = "needs_more_evidence"
    return LambdaM045DecisionRecord(
        decision_status=status if not blockers else "needs_more_evidence",
        selected_candidate=selected if not blockers else None,
        future_review_allowed=future_allowed and not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            "M045 decision is review-only",
            "immediate launch remains disabled",
        ],
    )


def load_lambda_m045_decision_record(path: str | Path) -> LambdaM045DecisionRecord:
    return LambdaM045DecisionRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m045_decision_record(
    path: str | Path,
    report: LambdaM045DecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
