"""Future-only M039 lower-cost launch authorization package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_budget_lock import (
    LambdaLowerCostBudgetLock,
    load_lambda_lower_cost_budget_lock,
)
from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    LambdaLowerCostCanonicalReadinessReport,
    load_lambda_lower_cost_canonical_readiness,
)
from decodilo.lambda_cloud.lower_cost_final_state_snapshot import (
    LambdaLowerCostFinalStateSnapshot,
    load_lambda_lower_cost_final_state_snapshot,
)
from decodilo.lambda_cloud.lower_cost_launch_window_lock import (
    LambdaLowerCostLaunchWindowLock,
    load_lambda_lower_cost_launch_window_lock,
)
from decodilo.lambda_cloud.lower_cost_operator_approval import (
    LambdaLowerCostOperatorApproval,
    load_lambda_lower_cost_operator_approval,
)
from decodilo.lambda_cloud.lower_cost_resource_lock import (
    LambdaLowerCostResourceLock,
    load_lambda_lower_cost_resource_lock,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    LambdaStrandResponseLossControlCheck,
    load_lambda_strand_response_loss_control_check,
)

LambdaLowerCostM039AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m039_lower_cost_launch_attempt",
]


class LambdaLowerCostM039Authorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaLowerCostM039AuthorizationStatus
    selected_shape: str = "gpu_1x_h100_pcie"
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    selected_ssh_key_hash: str | None = None
    launch_authorized_for_next_milestone: bool
    launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaLowerCostM039Authorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M039 authorization cannot authorize launch now")
        if self.launch_authorized_for_next_milestone and self.blockers:
            raise ValueError("M039 authorization cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_m039_authorization(
    *,
    canonical_readiness: LambdaLowerCostCanonicalReadinessReport,
    state_snapshot: LambdaLowerCostFinalStateSnapshot,
    budget_lock: LambdaLowerCostBudgetLock,
    resource_lock: LambdaLowerCostResourceLock,
    launch_window_lock: LambdaLowerCostLaunchWindowLock,
    operator_approval: LambdaLowerCostOperatorApproval,
    response_loss_controls: LambdaStrandResponseLossControlCheck,
) -> LambdaLowerCostM039Authorization:
    blockers: list[str] = []
    if not canonical_readiness.readiness_passed:
        blockers.extend(canonical_readiness.blockers or ["canonical_readiness_failed"])
    if not state_snapshot.snapshot_passed:
        blockers.extend(state_snapshot.blockers or ["state_snapshot_failed"])
    if not budget_lock.budget_lock_passed:
        blockers.extend(budget_lock.blockers or ["budget_lock_failed"])
    if not resource_lock.resource_lock_passed:
        blockers.extend(resource_lock.blockers or ["resource_lock_failed"])
    if not launch_window_lock.launch_window_lock_passed:
        blockers.extend(launch_window_lock.blockers or ["launch_window_lock_failed"])
    if not operator_approval.approval_passed:
        blockers.extend(operator_approval.blockers or ["operator_approval_incomplete"])
    if not response_loss_controls.controls_passed:
        blockers.extend(response_loss_controls.blockers or ["response_loss_controls_failed"])
    blockers = sorted(set(blockers))
    authorized = not blockers
    return LambdaLowerCostM039Authorization(
        authorization_status=(
            "authorized_for_future_m039_lower_cost_launch_attempt"
            if authorized
            else "not_authorized"
        ),
        estimated_30min_cost=canonical_readiness.planned_30min_cost,
        buffered_estimated_30min_cost=canonical_readiness.buffered_30min_cost,
        selected_ssh_key_hash=canonical_readiness.selected_ssh_key_hash,
        launch_authorized_for_next_milestone=authorized,
        blockers=blockers,
        warnings=[
            "M039 authorization is future-only and cannot execute launch now",
            "fresh operator confirmation remains required at execution milestone",
        ],
    )


def build_lambda_lower_cost_m039_authorization_from_paths(
    *,
    canonical_readiness: str | Path,
    state_snapshot: str | Path,
    budget_lock: str | Path,
    resource_lock: str | Path,
    launch_window_lock: str | Path,
    operator_approval: str | Path,
    response_loss_controls: str | Path,
) -> LambdaLowerCostM039Authorization:
    return build_lambda_lower_cost_m039_authorization(
        canonical_readiness=load_lambda_lower_cost_canonical_readiness(
            canonical_readiness
        ),
        state_snapshot=load_lambda_lower_cost_final_state_snapshot(state_snapshot),
        budget_lock=load_lambda_lower_cost_budget_lock(budget_lock),
        resource_lock=load_lambda_lower_cost_resource_lock(resource_lock),
        launch_window_lock=load_lambda_lower_cost_launch_window_lock(
            launch_window_lock
        ),
        operator_approval=load_lambda_lower_cost_operator_approval(operator_approval),
        response_loss_controls=load_lambda_strand_response_loss_control_check(
            response_loss_controls
        ),
    )


def load_lambda_lower_cost_m039_authorization(
    path: str | Path,
) -> LambdaLowerCostM039Authorization:
    return LambdaLowerCostM039Authorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_m039_authorization(
    path: str | Path,
    report: LambdaLowerCostM039Authorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
