"""Follow-up report for repeated Lambda capacity rejections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_error_closeout import (
    load_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.capacity_history import (
    load_lambda_capacity_history,
)
from decodilo.lambda_cloud.live_discovery_report import (
    load_lambda_live_discovery_report,
)

LambdaCapacityTeardownRiskStatus = Literal[
    "no_teardown_required_no_instance_created",
    "manual_review_required",
    "unresolved",
]
LambdaCapacityRecommendedStrategy = Literal[
    "wait_for_live_availability",
    "rotate_catalog_candidate",
    "operator_select_alternative",
    "pause_launches",
]


class LambdaCapacityFollowupReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    latest_closeout_status: str
    repeated_capacity_error_detected: bool
    termination_required: bool
    teardown_risk_status: LambdaCapacityTeardownRiskStatus
    same_fixed_shape_retry_blocked: bool
    recommended_strategy: LambdaCapacityRecommendedStrategy
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityFollowupReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity follow-up cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_followup_from_paths(
    *,
    history: str | Path,
    latest_closeout: str | Path,
    latest_discovery: str | Path | None = None,
) -> LambdaCapacityFollowupReport:
    capacity_history = load_lambda_capacity_history(history)
    closeout = load_lambda_capacity_error_closeout(latest_closeout)
    final_instance_count = closeout.final_instance_count
    final_unmanaged_count = closeout.final_unmanaged_count
    if latest_discovery is not None and Path(latest_discovery).exists():
        discovery = load_lambda_live_discovery_report(latest_discovery)
        final_instance_count = len(discovery.instances)
        final_unmanaged_count = len(discovery.unmanaged_instances)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["latest_capacity_closeout_not_succeeded"])
    no_instance_created = (
        closeout.capacity_error_confirmed
        and not closeout.owned_instance_id_present
        and final_instance_count == 0
        and final_unmanaged_count == 0
    )
    if no_instance_created:
        teardown_status: LambdaCapacityTeardownRiskStatus = (
            "no_teardown_required_no_instance_created"
        )
    elif closeout.closeout_succeeded:
        teardown_status = "manual_review_required"
    else:
        teardown_status = "unresolved"
    if capacity_history.repeated_capacity_error_detected:
        strategy: LambdaCapacityRecommendedStrategy = "rotate_catalog_candidate"
    else:
        strategy = "wait_for_live_availability"
    return LambdaCapacityFollowupReport(
        latest_closeout_status=closeout.closeout_status,
        repeated_capacity_error_detected=(
            capacity_history.repeated_capacity_error_detected
        ),
        termination_required=closeout.termination_required and not no_instance_created,
        teardown_risk_status=teardown_status,
        same_fixed_shape_retry_blocked=closeout.capacity_error_confirmed,
        recommended_strategy=strategy if not blockers else "pause_launches",
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        blockers=sorted(set(blockers)),
        warnings=[
            "capacity follow-up is review-only",
            "same fixed-shape retry is blocked without fresh availability evidence",
        ],
    )


def load_lambda_capacity_followup(
    path: str | Path,
) -> LambdaCapacityFollowupReport:
    return LambdaCapacityFollowupReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_followup(
    path: str | Path,
    report: LambdaCapacityFollowupReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
