"""Capacity-aware interpretation of Lambda launch run reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_error_closeout import (
    LambdaCapacityErrorCloseoutReport,
    load_lambda_capacity_error_closeout,
)

LambdaCapacityAwareLaunchOutcome = Literal[
    "capacity_rejected_no_instance_created",
    "response_loss_manual_review_required",
    "malformed_or_unknown_manual_review_required",
    "unresolved",
]


class LambdaCapacityAwareRunSemanticsReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_outcome: LambdaCapacityAwareLaunchOutcome
    termination_required: bool
    ownership_uncertain: bool
    manual_review_required_for_teardown: bool
    capacity_error_confirmed: bool
    provider_error_message_redacted: str | None = None
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityAwareRunSemanticsReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-aware semantics cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCapacityAwareRunSemantics = LambdaCapacityAwareRunSemanticsReport


def build_lambda_capacity_aware_run_semantics(
    closeout: LambdaCapacityErrorCloseoutReport,
) -> LambdaCapacityAwareRunSemanticsReport:
    capacity_no_instance = (
        closeout.status_code == 400
        and closeout.capacity_error_confirmed
        and not closeout.owned_instance_id_present
        and closeout.final_instance_count == 0
        and closeout.final_unmanaged_count == 0
    )
    if capacity_no_instance:
        outcome: LambdaCapacityAwareLaunchOutcome = "capacity_rejected_no_instance_created"
        termination_required = False
        ownership_uncertain = False
        manual_review = False
        blockers: list[str] = []
    elif closeout.launch_request_sent and closeout.status_code is None:
        outcome = "response_loss_manual_review_required"
        termination_required = False
        ownership_uncertain = True
        manual_review = True
        blockers = ["launch_response_missing_or_lost"]
    elif closeout.classification not in {"http_error_json", None}:
        outcome = "malformed_or_unknown_manual_review_required"
        termination_required = closeout.termination_required
        ownership_uncertain = True
        manual_review = True
        blockers = ["launch_response_malformed_or_unknown"]
    else:
        outcome = "unresolved"
        termination_required = closeout.termination_required
        ownership_uncertain = True
        manual_review = True
        blockers = closeout.blockers or ["capacity_closeout_unresolved"]
    return LambdaCapacityAwareRunSemanticsReport(
        launch_outcome=outcome,
        termination_required=termination_required,
        ownership_uncertain=ownership_uncertain,
        manual_review_required_for_teardown=manual_review,
        capacity_error_confirmed=closeout.capacity_error_confirmed,
        provider_error_message_redacted=closeout.provider_error_message_redacted,
        final_instance_count=closeout.final_instance_count,
        final_unmanaged_count=closeout.final_unmanaged_count,
        blockers=blockers,
        warnings=[
            "capacity-aware semantics are review-only",
            "generic M029 manual_review_required may be refined by closeout evidence",
        ],
    )


def build_lambda_capacity_aware_run_semantics_from_path(
    latest_closeout: str | Path,
) -> LambdaCapacityAwareRunSemanticsReport:
    return build_lambda_capacity_aware_run_semantics(
        load_lambda_capacity_error_closeout(latest_closeout)
    )


def load_lambda_capacity_aware_run_semantics(
    path: str | Path,
) -> LambdaCapacityAwareRunSemanticsReport:
    return LambdaCapacityAwareRunSemanticsReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_aware_run_semantics(
    path: str | Path,
    report: LambdaCapacityAwareRunSemanticsReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
