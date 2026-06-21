"""Retry policy after Lambda capacity rejections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history import load_lambda_capacity_history

LambdaCapacityAwareRetryRecommendation = Literal[
    "block_same_shape_retry",
    "allow_different_catalog_candidate_future_review",
    "allow_same_shape_future_review_with_live_availability",
    "wait_and_refresh_live_availability",
]


class LambdaCapacityAwareRetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    no_automatic_retry: bool = True
    same_shape_retry_blocked: bool
    catalog_candidate_rotation_allowed_for_future_review: bool
    live_availability_can_allow_same_shape_future_review: bool
    wait_and_refresh_preferred: bool
    recommendation: LambdaCapacityAwareRetryRecommendation
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityAwareRetryPolicy:
        if (
            not self.no_automatic_retry
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-aware retry policy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_aware_retry_policy_from_path(
    *,
    history: str | Path,
    live_availability_evidence_present: bool = False,
) -> LambdaCapacityAwareRetryPolicy:
    capacity_history = load_lambda_capacity_history(history)
    same_shape_blocked = bool(capacity_history.shapes_with_capacity_errors)
    if live_availability_evidence_present:
        recommendation: LambdaCapacityAwareRetryRecommendation = (
            "allow_same_shape_future_review_with_live_availability"
        )
    elif capacity_history.capacity_error_count > 0:
        recommendation = "allow_different_catalog_candidate_future_review"
    else:
        recommendation = "wait_and_refresh_live_availability"
    return LambdaCapacityAwareRetryPolicy(
        same_shape_retry_blocked=same_shape_blocked
        and not live_availability_evidence_present,
        catalog_candidate_rotation_allowed_for_future_review=(
            capacity_history.capacity_error_count > 0
        ),
        live_availability_can_allow_same_shape_future_review=True,
        wait_and_refresh_preferred=not live_availability_evidence_present,
        recommendation=(
            "block_same_shape_retry"
            if same_shape_blocked and not live_availability_evidence_present
            else recommendation
        ),
        warnings=[
            "no automatic retry is allowed after capacity rejection",
            "same-shape future review requires fresh live availability evidence",
        ],
    )


def load_lambda_capacity_aware_retry_policy(
    path: str | Path,
) -> LambdaCapacityAwareRetryPolicy:
    return LambdaCapacityAwareRetryPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_aware_retry_policy(
    path: str | Path,
    report: LambdaCapacityAwareRetryPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
