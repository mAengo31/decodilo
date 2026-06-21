"""M029 first-launch spend estimate audit."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaM029SpendAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    planned_max_budget: float = 50.0
    estimated_hourly_cost: float
    actual_elapsed_seconds: float
    estimated_spend: float
    safety_buffer: float = 0.0
    budget_exceeded: bool
    runtime_exceeded: bool
    billable_action_performed: bool
    launch_request_sent: bool
    terminate_request_sent: bool
    termination_verified: bool
    launch_outcome: str | None = None
    termination_required: bool | None = None
    manual_review_required_for_teardown: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_m029_spend_audit(
    *,
    estimated_hourly_cost: float,
    elapsed_seconds: float,
    launch_request_sent: bool,
    terminate_request_sent: bool,
    termination_verified: bool,
    billable_action_performed: bool | None = None,
    launch_outcome: str | None = None,
    termination_required: bool | None = None,
    manual_review_required_for_teardown: bool | None = None,
    planned_max_budget: float = 50.0,
    max_runtime_minutes: int = 30,
    safety_buffer: float = 0.0,
) -> LambdaM029SpendAuditReport:
    estimated = estimated_hourly_cost * (elapsed_seconds / 3600.0) + safety_buffer
    warnings: list[str] = []
    runtime_exceeded = elapsed_seconds > max_runtime_minutes * 60
    if runtime_exceeded:
        warnings.append("elapsed runtime exceeded M029 limit")
    if not termination_verified and launch_request_sent and termination_required is not False:
        warnings.append("termination not verified; manual review required")
    return LambdaM029SpendAuditReport(
        estimated_hourly_cost=estimated_hourly_cost,
        actual_elapsed_seconds=elapsed_seconds,
        estimated_spend=estimated,
        safety_buffer=safety_buffer,
        budget_exceeded=estimated > planned_max_budget,
        runtime_exceeded=runtime_exceeded,
        billable_action_performed=(
            launch_request_sent
            if billable_action_performed is None
            else billable_action_performed
        ),
        launch_request_sent=launch_request_sent,
        terminate_request_sent=terminate_request_sent,
        termination_verified=termination_verified,
        launch_outcome=launch_outcome,
        termination_required=termination_required,
        manual_review_required_for_teardown=manual_review_required_for_teardown,
        warnings=warnings,
    )


def write_lambda_m029_spend_audit(path: str | Path, report: LambdaM029SpendAuditReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
