"""Gate check for future M046 capacity-selected launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    load_lambda_capacity_selected_cost_risk_review,
)
from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    load_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)


class LambdaCapacitySelectedGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    cost_risk_review_status: str
    operator_approval_status: str
    m046_authorization_status: str
    response_capture_active: bool = False
    effective_launch_timeout_seconds: float | None = None
    no_auto_launch_retry: bool = True
    selected_ssh_key_hash: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacitySelectedGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("capacity-selected gate cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_selected_gate_check_from_paths(
    *,
    authorization: str | Path,
    cost_risk_review: str | Path,
    operator_approval: str | Path,
    response_loss_controls: str | Path,
) -> LambdaCapacitySelectedGateCheck:
    auth = load_lambda_capacity_selected_m046_authorization(authorization)
    cost = load_lambda_capacity_selected_cost_risk_review(cost_risk_review)
    approval = load_lambda_capacity_selected_operator_approval(operator_approval)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = [*auth.blockers, *cost.blockers, *approval.blockers, *controls.blockers]
    if (
        auth.authorization_status
        != "authorized_for_future_m046_capacity_selected_launch_review"
    ):
        blockers.append("m046_capacity_selected_authorization_not_ready")
    if not cost.cost_risk_review_passed:
        blockers.append("capacity_selected_cost_risk_review_not_passed")
    if (
        approval.approval_status
        != "approved_for_future_m046_capacity_selected_launch_review"
    ):
        blockers.append("capacity_selected_operator_approval_not_approved")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    return LambdaCapacitySelectedGateCheck(
        gate_passed=not blockers,
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source,
        cost_risk_review_status=(
            "passed" if cost.cost_risk_review_passed else "blocked"
        ),
        operator_approval_status=approval.approval_status,
        m046_authorization_status=auth.authorization_status,
        response_capture_active=controls.response_capture_active,
        effective_launch_timeout_seconds=controls.timeout_seconds,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        selected_ssh_key_hash=auth.selected_ssh_key_hash,
        blockers=sorted(set(blockers)),
        warnings=[
            "gate check is future-review only",
            "M045 does not authorize immediate launch",
        ],
    )


def load_lambda_capacity_selected_gate_check(path: str | Path) -> LambdaCapacitySelectedGateCheck:
    return LambdaCapacitySelectedGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_gate_check(
    path: str | Path,
    report: LambdaCapacitySelectedGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
