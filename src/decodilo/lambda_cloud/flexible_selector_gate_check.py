"""Gate check for future flexible availability-first launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.flexible_selector_authorization import (
    load_lambda_flexible_selector_authorization,
)


class LambdaFlexibleSelectorGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_candidate_reason: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    existing_ssh_key_available: bool = False
    selected_ssh_key_hash: str | None = None
    response_capture_active: bool = False
    no_auto_launch_retry: bool = True
    strand_payload_compatible: bool = False
    fixed_shape_path_used: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFlexibleSelectorGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.fixed_shape_path_used
            or not self.no_auto_launch_retry
        ):
            raise ValueError("flexible-selector gate cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_flexible_selector_gate_check_from_paths(
    *,
    authorization: str | Path,
    selector_output: str | Path,
) -> LambdaFlexibleSelectorGateCheck:
    auth = load_lambda_flexible_selector_authorization(authorization)
    selector = load_lambda_availability_first_candidate_ranker(selector_output)
    candidate = selector.selected_candidate
    blockers = [*auth.blockers, *selector.blockers]
    if auth.authorization_status != "authorized_for_future_flexible_selector_launch_review":
        blockers.append("flexible_selector_authorization_not_ready")
    if candidate is None:
        blockers.append("selector_candidate_missing")
    elif candidate.shape != auth.selected_candidate:
        blockers.append("authorization_selector_candidate_mismatch")
    if auth.authorization_source != "flexible_selector_output":
        blockers.append("authorization_not_from_flexible_selector")
    if auth.fixed_shape_path_used:
        blockers.append("fixed_shape_path_used")
    return LambdaFlexibleSelectorGateCheck(
        gate_passed=not blockers,
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source,
        selected_candidate_reason=auth.selected_candidate_reason,
        estimated_30min_cost=auth.estimated_30min_cost,
        buffered_estimated_30min_cost=auth.buffered_estimated_30min_cost,
        existing_ssh_key_available=auth.selected_ssh_key_hash is not None,
        selected_ssh_key_hash=auth.selected_ssh_key_hash,
        response_capture_active=True,
        no_auto_launch_retry=auth.no_auto_launch_retry,
        strand_payload_compatible=(
            False if candidate is None else candidate.strand_payload_compatible
        ),
        fixed_shape_path_used=False,
        blockers=sorted(set(blockers)),
        warnings=[
            "gate check is future-review only",
            "command execution remains disabled in M044G",
        ],
    )


def load_lambda_flexible_selector_gate_check(
    path: str | Path,
) -> LambdaFlexibleSelectorGateCheck:
    return LambdaFlexibleSelectorGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_flexible_selector_gate_check(
    path: str | Path,
    report: LambdaFlexibleSelectorGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
