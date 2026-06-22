"""Decision record for future SSH retry after capacity rejection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    load_lambda_ssh_live_candidate_selection,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    load_lambda_ssh_retry_candidate_policy,
)

LambdaSSHRetryOperatorDecisionStatus = Literal[
    "wait_for_fresh_live_availability",
    "authorize_future_live_candidate_ssh_retry_review",
    "pause_ssh_work",
    "needs_more_evidence",
]


class LambdaSSHRetryOperatorDecisionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaSSHRetryOperatorDecisionStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHRetryOperatorDecisionReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.decision_status in {"launch_now", "ssh_now"}  # type: ignore[comparison-overlap]
        ):
            raise ValueError("SSH retry operator decision cannot enable launch or SSH")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_retry_operator_decision_from_paths(
    *,
    candidate_selection: str | Path,
    retry_policy: str | Path,
) -> LambdaSSHRetryOperatorDecisionReport:
    selection = load_lambda_ssh_live_candidate_selection(candidate_selection)
    policy = load_lambda_ssh_retry_candidate_policy(retry_policy)
    blockers = [*selection.blockers, *policy.blockers]
    if (
        selection.selection_status == "selected_live_candidate"
        and policy.policy_status == "policy_passed"
    ):
        status: LambdaSSHRetryOperatorDecisionStatus = (
            "authorize_future_live_candidate_ssh_retry_review"
        )
    elif selection.selection_status == "no_candidate_wait_for_availability":
        status = "wait_for_fresh_live_availability"
    else:
        status = "needs_more_evidence"
    if blockers and status == "authorize_future_live_candidate_ssh_retry_review":
        status = "needs_more_evidence"
    return LambdaSSHRetryOperatorDecisionReport(
        decision_status=status,
        selected_candidate=selection.selected_candidate,
        selected_region=selection.selected_region,
        blockers=sorted(set(blockers)),
        warnings=[
            "decision is future-review only",
            "immediate launch and immediate SSH remain forbidden",
        ],
    )


def load_lambda_ssh_retry_operator_decision(
    path: str | Path,
) -> LambdaSSHRetryOperatorDecisionReport:
    return LambdaSSHRetryOperatorDecisionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_retry_operator_decision(
    path: str | Path,
    report: LambdaSSHRetryOperatorDecisionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
