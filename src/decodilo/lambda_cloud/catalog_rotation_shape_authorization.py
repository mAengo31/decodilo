"""Future-only M045 authorization for an accepted catalog-rotation shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    load_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_history import load_lambda_capacity_history
from decodilo.lambda_cloud.catalog_candidate_rotation import (
    load_lambda_catalog_candidate_rotation,
)
from decodilo.lambda_cloud.catalog_rotation_cost_review import (
    CATALOG_ROTATION_PRIOR_FAILED_CANDIDATE,
    CATALOG_ROTATION_SELECTED_CANDIDATE,
    load_lambda_catalog_rotation_cost_review,
)
from decodilo.lambda_cloud.catalog_rotation_operator_decision import (
    load_lambda_catalog_rotation_operator_decision,
)
from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    load_lambda_catalog_rotation_risk_acceptance,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)

LambdaCatalogRotationShapeAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m045_catalog_rotation_launch_review",
]


class LambdaCatalogRotationShapeAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaCatalogRotationShapeAuthorizationStatus
    selected_candidate: str | None = None
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
    def _validate_future_only(self) -> LambdaCatalogRotationShapeAuthorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("catalog-rotation authorization cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_rotation_shape_authorization_from_paths(
    *,
    capacity_history: str | Path,
    retry_policy: str | Path,
    rotation_rank: str | Path,
    cost_review: str | Path,
    risk_acceptance: str | Path,
    operator_decision: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
) -> LambdaCatalogRotationShapeAuthorization:
    history = load_lambda_capacity_history(capacity_history)
    retry = load_lambda_capacity_aware_retry_policy(retry_policy)
    rotation = load_lambda_catalog_candidate_rotation(rotation_rank)
    cost = load_lambda_catalog_rotation_cost_review(cost_review)
    risk = load_lambda_catalog_rotation_risk_acceptance(risk_acceptance)
    decision = load_lambda_catalog_rotation_operator_decision(operator_decision)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = [
        *history.blockers,
        *retry.blockers,
        *rotation.blockers,
        *cost.blockers,
        *risk.blockers,
        *decision.blockers,
        *ssh.errors,
        *controls.blockers,
    ]
    if not history.repeated_capacity_error_detected:
        blockers.append("repeated_capacity_error_not_confirmed")
    if CATALOG_ROTATION_PRIOR_FAILED_CANDIDATE not in history.shapes_with_capacity_errors:
        blockers.append("prior_failed_shape_not_in_capacity_history")
    if not retry.same_shape_retry_blocked:
        blockers.append("same_shape_retry_not_blocked")
    if not retry.no_automatic_retry:
        blockers.append("automatic_retry_not_disabled")
    if rotation.selected_candidate is None:
        blockers.append("catalog_rotation_candidate_missing")
    elif rotation.selected_candidate.shape != CATALOG_ROTATION_SELECTED_CANDIDATE:
        blockers.append("catalog_rotation_selected_candidate_mismatch")
    if not cost.cost_review_passed:
        blockers.append("catalog_rotation_cost_review_not_passed")
    if risk.acceptance_status != "accepted_gpu_8x_a100_80gb_sxm4_for_future_review":
        blockers.append("catalog_rotation_risk_not_accepted")
    if decision.decision_status != "accept_selected_catalog_rotation_candidate":
        blockers.append("catalog_rotation_operator_decision_not_accept")
    if not ssh.selection_passed or ssh.selected_ssh_key_name_redacted_or_hash is None:
        blockers.append("existing_ssh_key_selection_required")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    passed = not blockers
    return LambdaCatalogRotationShapeAuthorization(
        authorization_status=(
            "authorized_for_future_m045_catalog_rotation_launch_review"
            if passed
            else "not_authorized"
        ),
        selected_candidate=CATALOG_ROTATION_SELECTED_CANDIDATE if passed else None,
        selected_region=(
            None
            if not passed or rotation.selected_candidate is None
            else rotation.selected_candidate.region
        ),
        selected_ssh_key_hash=(
            ssh.selected_ssh_key_name_redacted_or_hash if passed else None
        ),
        estimated_30min_cost=cost.estimated_30min_cost if passed else None,
        buffered_estimated_30min_cost=(
            cost.buffered_estimated_30min_cost if passed else None
        ),
        launch_authorized_for_next_milestone=passed,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-review only",
            "M045 remains a separate supervised billable milestone",
        ],
    )


def load_lambda_catalog_rotation_shape_authorization(
    path: str | Path,
) -> LambdaCatalogRotationShapeAuthorization:
    return LambdaCatalogRotationShapeAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_shape_authorization(
    path: str | Path,
    report: LambdaCatalogRotationShapeAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
