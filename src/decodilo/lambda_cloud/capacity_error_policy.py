"""Capacity-error retry policy for Lambda lifecycle smoke attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_error_closeout import (
    LambdaCapacityErrorCloseoutReport,
    load_lambda_capacity_error_closeout,
)

LambdaCapacityRetryStrategy = Literal[
    "availability_first_required",
    "operator_wait_and_retry_for_future_review",
    "unresolved",
]


class LambdaCapacityErrorPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    no_immediate_automatic_retry: bool = True
    same_shape_retry_blocked_without_fresh_availability: bool
    availability_first_selector_required: bool
    lower_cost_or_alternative_shape_preferred: bool = True
    operator_wait_and_retry_accepted_for_future_review: bool = False
    retry_strategy: LambdaCapacityRetryStrategy
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityErrorPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity error policy cannot enable launch")
        if not self.no_immediate_automatic_retry:
            raise ValueError("capacity error policy must forbid automatic retry")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_error_policy(
    *,
    closeout: LambdaCapacityErrorCloseoutReport,
    operator_accepts_wait_and_retry_for_future_review: bool = False,
) -> LambdaCapacityErrorPolicyReport:
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("capacity_error_closeout_not_succeeded")
    same_shape_blocked = closeout.capacity_error_confirmed
    availability_required = closeout.capacity_error_confirmed
    if operator_accepts_wait_and_retry_for_future_review and not closeout.closeout_succeeded:
        blockers.append("operator_wait_retry_requires_closed_capacity_error")
    if operator_accepts_wait_and_retry_for_future_review and closeout.closeout_succeeded:
        strategy: LambdaCapacityRetryStrategy = "operator_wait_and_retry_for_future_review"
    elif closeout.closeout_succeeded:
        strategy = "availability_first_required"
    else:
        strategy = "unresolved"
    return LambdaCapacityErrorPolicyReport(
        same_shape_retry_blocked_without_fresh_availability=same_shape_blocked,
        availability_first_selector_required=availability_required,
        operator_wait_and_retry_accepted_for_future_review=(
            operator_accepts_wait_and_retry_for_future_review and not blockers
        ),
        retry_strategy=strategy,
        blockers=blockers,
        warnings=[
            "no automatic retry is allowed after a capacity rejection",
            (
                "same fixed-shape retry requires fresh availability evidence "
                "and renewed operator approval"
            ),
            "availability-first selection is preferred for lifecycle smoke testing",
        ],
    )


def build_lambda_capacity_error_policy_from_path(
    closeout: str | Path,
    *,
    operator_accepts_wait_and_retry_for_future_review: bool = False,
) -> LambdaCapacityErrorPolicyReport:
    return build_lambda_capacity_error_policy(
        closeout=load_lambda_capacity_error_closeout(closeout),
        operator_accepts_wait_and_retry_for_future_review=(
            operator_accepts_wait_and_retry_for_future_review
        ),
    )


def load_lambda_capacity_error_policy(path: str | Path) -> LambdaCapacityErrorPolicyReport:
    return LambdaCapacityErrorPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_error_policy(
    path: str | Path,
    report: LambdaCapacityErrorPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
