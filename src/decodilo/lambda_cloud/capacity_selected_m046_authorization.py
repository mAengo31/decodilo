"""Future-only M046 authorization for the capacity-history-selected candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)
from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    load_lambda_capacity_history_selector_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    CAPACITY_SELECTED_CANDIDATE,
    load_lambda_capacity_selected_cost_risk_review,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    load_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)

LambdaCapacitySelectedM046AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m046_capacity_selected_launch_review",
]


class LambdaCapacitySelectedM046Authorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaCapacitySelectedM046AuthorizationStatus
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_region: str | None = None
    selected_ssh_key_hash: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    launch_authorized_for_next_milestone: bool = False
    launch_authorized_now: bool = False
    no_auto_launch_retry: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaCapacitySelectedM046Authorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("M046 authorization cannot enable immediate launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_selected_m046_authorization_from_paths(
    *,
    cost_risk_review: str | Path,
    operator_approval: str | Path,
    selector_authorization: str | Path,
    selector_gate_check: str | Path,
    response_loss_controls: str | Path,
    ssh_key_selection: str | Path,
) -> LambdaCapacitySelectedM046Authorization:
    cost = load_lambda_capacity_selected_cost_risk_review(cost_risk_review)
    approval = load_lambda_capacity_selected_operator_approval(operator_approval)
    selector_auth = load_lambda_capacity_history_selector_authorization(
        selector_authorization
    )
    selector_gate = load_lambda_capacity_history_selector_gate_check(selector_gate_check)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    blockers = [
        *cost.blockers,
        *approval.blockers,
        *selector_auth.blockers,
        *selector_gate.blockers,
        *controls.blockers,
        *ssh.errors,
    ]
    if not cost.cost_risk_review_passed:
        blockers.append("capacity_selected_cost_risk_review_not_passed")
    if (
        approval.approval_status
        != "approved_for_future_m046_capacity_selected_launch_review"
    ):
        blockers.append("capacity_selected_operator_approval_not_approved")
    if (
        selector_auth.authorization_status
        != "authorized_for_future_capacity_history_selector_review"
    ):
        blockers.append("capacity_history_selector_authorization_not_ready")
    if not selector_gate.gate_passed:
        blockers.append("capacity_history_selector_gate_not_passed")
    if selector_auth.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("selector_authorization_candidate_mismatch")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    if not ssh.selection_passed or ssh.selected_ssh_key_name_redacted_or_hash is None:
        blockers.append("existing_ssh_key_selection_required")
    if not cost.non_sample_price:
        blockers.append("non_sample_price_required")
    passed = not blockers
    return LambdaCapacitySelectedM046Authorization(
        authorization_status=(
            "authorized_for_future_m046_capacity_selected_launch_review"
            if passed
            else "not_authorized"
        ),
        selected_candidate=CAPACITY_SELECTED_CANDIDATE if passed else None,
        selected_candidate_source=cost.candidate_source if passed else None,
        selected_region=cost.selected_region if passed else None,
        selected_ssh_key_hash=(
            ssh.selected_ssh_key_name_redacted_or_hash if passed else None
        ),
        estimated_30min_cost=cost.estimated_30min_cost if passed else None,
        buffered_estimated_30min_cost=(
            cost.buffered_estimated_30min_cost if passed else None
        ),
        launch_authorized_for_next_milestone=passed,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-review only",
            "M046 remains a separate supervised billable milestone",
        ],
    )


def load_lambda_capacity_selected_m046_authorization(
    path: str | Path,
) -> LambdaCapacitySelectedM046Authorization:
    return LambdaCapacitySelectedM046Authorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_m046_authorization(
    path: str | Path,
    report: LambdaCapacitySelectedM046Authorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
