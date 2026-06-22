"""Future-only M056 authorization for SSH retry with a live candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    load_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    load_lambda_ssh_live_candidate_selection,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    load_lambda_ssh_retry_candidate_policy,
)
from decodilo.lambda_cloud.ssh_retry_operator_decision import (
    load_lambda_ssh_retry_operator_decision,
)

LambdaSSHM056AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m056_live_candidate_ssh_retry_review",
]


class LambdaSSHM056AuthorizationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaSSHM056AuthorizationStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    future_m056_review_authorized: bool
    launch_authorized_now: bool = False
    ssh_authorized_now: bool = False
    max_launch_attempts: int = 1
    max_ssh_attempts: int = 1
    no_auto_retry: bool = True
    no_remote_command: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHM056AuthorizationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
            or self.ssh_authorized_now
            or not self.no_auto_retry
        ):
            raise ValueError("M056 SSH retry authorization must be future-only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_retry_future_authorization_from_paths(
    *,
    capacity_closeout: str | Path,
    candidate_selection: str | Path,
    retry_policy: str | Path,
    operator_decision: str | Path,
) -> LambdaSSHM056AuthorizationReport:
    closeout = load_lambda_ssh_capacity_retry_closeout(capacity_closeout)
    selection = load_lambda_ssh_live_candidate_selection(candidate_selection)
    policy = load_lambda_ssh_retry_candidate_policy(retry_policy)
    decision = load_lambda_ssh_retry_operator_decision(operator_decision)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["capacity_closeout_not_succeeded"])
    if selection.selection_status != "selected_live_candidate":
        blockers.extend(selection.blockers or ["live_candidate_not_selected"])
    if policy.policy_status != "policy_passed":
        blockers.extend(policy.blockers or ["retry_policy_not_passed"])
    if decision.decision_status != "authorize_future_live_candidate_ssh_retry_review":
        blockers.extend(decision.blockers or ["operator_decision_not_future_authorized"])
    authorized = not blockers
    return LambdaSSHM056AuthorizationReport(
        authorization_status=(
            "authorized_for_future_m056_live_candidate_ssh_retry_review"
            if authorized
            else "not_authorized"
        ),
        selected_candidate=selection.selected_candidate,
        selected_region=selection.selected_region,
        selected_candidate_source=selection.selected_candidate_source,
        future_m056_review_authorized=authorized,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only and does not permit immediate launch or SSH",
            "future M056 must regenerate live read-only discovery before launch",
        ],
    )


def load_lambda_ssh_retry_future_authorization(
    path: str | Path,
) -> LambdaSSHM056AuthorizationReport:
    return LambdaSSHM056AuthorizationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_retry_future_authorization(
    path: str | Path,
    report: LambdaSSHM056AuthorizationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
