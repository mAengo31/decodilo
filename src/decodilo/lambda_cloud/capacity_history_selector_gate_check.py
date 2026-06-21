"""Gate check for capacity-history-aware selector future review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)


class LambdaCapacityHistorySelectorGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    recent_capacity_failure_excluded_candidates: list[str] = Field(default_factory=list)
    selected_candidate_has_recent_capacity_failure: bool = False
    same_shape_retry_acceptance_required: bool = False
    same_shape_retry_acceptance_present: bool = False
    response_capture_active: bool = False
    no_auto_launch_retry: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityHistorySelectorGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("capacity-history selector gate cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_history_selector_gate_check_from_paths(
    *,
    authorization: str | Path,
    selector_output: str | Path,
) -> LambdaCapacityHistorySelectorGateCheck:
    auth = load_lambda_capacity_history_selector_authorization(authorization)
    selector = load_lambda_capacity_history_aware_selector(selector_output)
    blockers = [*auth.blockers, *selector.blockers]
    if (
        auth.authorization_status
        != "authorized_for_future_capacity_history_selector_review"
    ):
        blockers.append("capacity_history_selector_authorization_not_ready")
    if selector.selected_candidate is None:
        blockers.append("capacity_history_selector_candidate_missing")
    elif selector.selected_candidate.shape != auth.selected_candidate:
        blockers.append("authorization_selector_candidate_mismatch")
    return LambdaCapacityHistorySelectorGateCheck(
        gate_passed=not blockers,
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source,
        recent_capacity_failure_excluded_candidates=(
            selector.recent_capacity_failure_excluded_candidates
        ),
        selected_candidate_has_recent_capacity_failure=(
            auth.selected_candidate_has_recent_capacity_failure
        ),
        same_shape_retry_acceptance_required=auth.same_shape_retry_acceptance_required,
        same_shape_retry_acceptance_present=auth.same_shape_retry_acceptance_present,
        response_capture_active=True,
        no_auto_launch_retry=auth.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=[
            "gate check is future-review only",
            "capacity-failed shapes are excluded by default",
        ],
    )


def load_lambda_capacity_history_selector_gate_check(
    path: str | Path,
) -> LambdaCapacityHistorySelectorGateCheck:
    return LambdaCapacityHistorySelectorGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history_selector_gate_check(
    path: str | Path,
    report: LambdaCapacityHistorySelectorGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
