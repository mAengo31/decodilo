"""Future-only authorization package for availability-first Lambda launch review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.availability_first_launch_plan import (
    load_lambda_availability_first_launch_plan,
)
from decodilo.lambda_cloud.capacity_error_closeout import (
    load_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.capacity_error_policy import (
    load_lambda_capacity_error_policy,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)

LambdaAvailabilityFirstAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_availability_first_launch_review",
]


class LambdaAvailabilityFirstArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaAvailabilityFirstAuthorizationPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    capacity_closeout_ref: LambdaAvailabilityFirstArtifactRef
    capacity_policy_ref: LambdaAvailabilityFirstArtifactRef | None = None
    rank_ref: LambdaAvailabilityFirstArtifactRef
    plan_ref: LambdaAvailabilityFirstArtifactRef
    ssh_key_selection_ref: LambdaAvailabilityFirstArtifactRef | None = None
    response_loss_controls_ref: LambdaAvailabilityFirstArtifactRef | None = None
    authorization_status: LambdaAvailabilityFirstAuthorizationStatus
    operator_approval_required_for_future_launch: bool = True
    operator_risk_acceptance_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAvailabilityFirstAuthorizationPackage:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("availability-first authorization cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_availability_first_authorization_package(
    *,
    capacity_closeout: str | Path,
    rank: str | Path,
    plan: str | Path,
    capacity_policy: str | Path | None = None,
    ssh_key_selection: str | Path | None = None,
    response_loss_controls: str | Path | None = None,
) -> LambdaAvailabilityFirstAuthorizationPackage:
    blockers: list[str] = []
    closeout = load_lambda_capacity_error_closeout(capacity_closeout)
    ranking = load_lambda_availability_first_candidate_ranker(rank)
    launch_plan = load_lambda_availability_first_launch_plan(plan)
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["capacity_error_closeout_not_succeeded"])
    if capacity_policy is not None:
        policy = load_lambda_capacity_error_policy(capacity_policy)
        if policy.blockers:
            blockers.extend(policy.blockers)
        if not policy.availability_first_selector_required:
            blockers.append("capacity_policy_does_not_require_availability_first_selector")
    if ranking.selected_candidate is None:
        blockers.extend(ranking.blockers or ["availability_first_candidate_not_selected"])
    if not launch_plan.plan_passed:
        blockers.extend(launch_plan.blockers or ["availability_first_launch_plan_failed"])
    if ssh_key_selection is not None:
        ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
        if not ssh.selection_passed:
            blockers.extend(ssh.errors or ["ssh_key_selection_failed"])
    if response_loss_controls is not None:
        controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
        if not controls.controls_passed:
            blockers.extend(controls.blockers or ["response_loss_controls_failed"])
    return LambdaAvailabilityFirstAuthorizationPackage(
        capacity_closeout_ref=_ref(capacity_closeout),
        capacity_policy_ref=None if capacity_policy is None else _ref(capacity_policy),
        rank_ref=_ref(rank),
        plan_ref=_ref(plan),
        ssh_key_selection_ref=None
        if ssh_key_selection is None
        else _ref(ssh_key_selection),
        response_loss_controls_ref=None
        if response_loss_controls is None
        else _ref(response_loss_controls),
        authorization_status=(
            "authorized_for_future_availability_first_launch_review"
            if not blockers
            else "not_authorized"
        ),
        operator_risk_acceptance_required=ranking.operator_risk_acceptance_required,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is for future review only",
            "operator approval is still required before any billable launch",
        ],
    )


def _ref(path: str | Path) -> LambdaAvailabilityFirstArtifactRef:
    target = Path(path)
    return LambdaAvailabilityFirstArtifactRef(
        path=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )


def load_lambda_availability_first_authorization_package(
    path: str | Path,
) -> LambdaAvailabilityFirstAuthorizationPackage:
    return LambdaAvailabilityFirstAuthorizationPackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_availability_first_authorization_package(
    path: str | Path,
    report: LambdaAvailabilityFirstAuthorizationPackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
