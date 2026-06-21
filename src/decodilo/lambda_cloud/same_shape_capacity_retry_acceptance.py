"""Explicit acceptance for same-shape retry after Lambda capacity failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSameShapeCapacityRetryAcceptanceStatus = Literal[
    "not_provided",
    "accepted_for_future_same_shape_capacity_retry_review",
    "declined",
]

_ACK_FIELDS = (
    "understands_same_shape_recent_capacity_failure",
    "understands_same_capacity_error_may_repeat",
    "understands_no_automatic_launch_retry",
    "understands_one_instance_only",
    "understands_no_instance_may_be_created",
    "understands_owned_termination_required_if_created",
    "understands_termination_verification_required",
    "understands_os_shutdown_insufficient",
    "understands_future_review_only",
)


class LambdaSameShapeCapacityRetryAcceptance(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    shape: str
    acceptance_status: LambdaSameShapeCapacityRetryAcceptanceStatus = "not_provided"
    understands_same_shape_recent_capacity_failure: bool = False
    understands_same_capacity_error_may_repeat: bool = False
    understands_no_automatic_launch_retry: bool = False
    understands_one_instance_only: bool = False
    understands_no_instance_may_be_created: bool = False
    understands_owned_termination_required_if_created: bool = False
    understands_termination_verification_required: bool = False
    understands_os_shutdown_insufficient: bool = False
    understands_future_review_only: bool = False
    acceptance_complete: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSameShapeCapacityRetryAcceptance:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("same-shape retry acceptance cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSameShapeCapacityRetryAcceptanceReport = LambdaSameShapeCapacityRetryAcceptance


def build_lambda_same_shape_capacity_retry_acceptance(
    *,
    shape: str,
    acknowledge_all: bool = False,
    decline: bool = False,
) -> LambdaSameShapeCapacityRetryAcceptance:
    ack_values = {field: acknowledge_all for field in _ACK_FIELDS}
    blockers: list[str] = []
    status: LambdaSameShapeCapacityRetryAcceptanceStatus = "not_provided"
    complete = False
    if decline:
        status = "declined"
        complete = True
    elif acknowledge_all:
        status = "accepted_for_future_same_shape_capacity_retry_review"
        complete = True
    else:
        blockers.extend(f"missing_acknowledgement:{field}" for field in _ACK_FIELDS)
    return LambdaSameShapeCapacityRetryAcceptance(
        shape=shape,
        acceptance_status=status,
        acceptance_complete=complete,
        blockers=sorted(set(blockers)),
        warnings=[
            "same-shape retry acceptance is future-review only",
            "M044H does not authorize immediate launch",
        ],
        **ack_values,
    )


def load_lambda_same_shape_capacity_retry_acceptance(
    path: str | Path,
) -> LambdaSameShapeCapacityRetryAcceptance:
    return LambdaSameShapeCapacityRetryAcceptance.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_same_shape_capacity_retry_acceptance(
    path: str | Path,
    report: LambdaSameShapeCapacityRetryAcceptance,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
