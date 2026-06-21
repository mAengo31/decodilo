"""Capacity-error history for Lambda lifecycle-smoke launch attempts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_error_closeout import (
    LambdaCapacityErrorCloseoutReport,
    load_lambda_capacity_error_closeout,
)


class LambdaCapacityAttemptRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_id: str
    selected_shape: str | None = None
    selected_region: str | None = None
    request_sent: bool
    response_received: bool | None = None
    status_code: int | None = None
    provider_error_message_redacted: str | None = None
    capacity_error_confirmed: bool
    owned_instance_created: bool
    termination_required: bool
    final_instance_count: int
    final_unmanaged_count: int
    estimated_spend: float | None = None
    closeout_status: str


class LambdaCapacityHistoryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    attempts: list[LambdaCapacityAttemptRecord] = Field(default_factory=list)
    attempts_analyzed: int
    capacity_error_count: int
    repeated_capacity_error_detected: bool
    shapes_with_capacity_errors: list[str] = Field(default_factory=list)
    regions_with_capacity_errors: list[str] = Field(default_factory=list)
    same_shape_retry_recommended: bool = False
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityHistoryReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.same_shape_retry_recommended
        ):
            raise ValueError("capacity history cannot enable or recommend launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCapacityHistory = LambdaCapacityHistoryReport


def build_lambda_capacity_history_from_paths(
    *,
    latest_closeout: str | Path,
    previous_closeout: str | Path | None = None,
) -> LambdaCapacityHistoryReport:
    records: list[LambdaCapacityAttemptRecord] = []
    if previous_closeout is not None and Path(previous_closeout).exists():
        records.append(
            _record_from_closeout(
                "previous-capacity-attempt",
                load_lambda_capacity_error_closeout(previous_closeout),
            )
        )
    records.append(
        _record_from_closeout(
            "latest-capacity-attempt",
            load_lambda_capacity_error_closeout(latest_closeout),
        )
    )
    capacity_records = [record for record in records if record.capacity_error_confirmed]
    shapes = sorted(
        {
            record.selected_shape
            for record in capacity_records
            if record.selected_shape is not None
        }
    )
    regions = sorted(
        {
            record.selected_region
            for record in capacity_records
            if record.selected_region is not None
        }
    )
    same_shape_counts = {
        shape: sum(1 for record in capacity_records if record.selected_shape == shape)
        for shape in shapes
    }
    repeated = any(count >= 2 for count in same_shape_counts.values())
    return LambdaCapacityHistoryReport(
        attempts=records,
        attempts_analyzed=len(records),
        capacity_error_count=len(capacity_records),
        repeated_capacity_error_detected=repeated,
        shapes_with_capacity_errors=shapes,
        regions_with_capacity_errors=regions,
        warnings=[
            "capacity history is review-only",
            "same-shape retry remains blocked by default after capacity errors",
        ],
    )


def _record_from_closeout(
    attempt_id: str,
    closeout: LambdaCapacityErrorCloseoutReport,
) -> LambdaCapacityAttemptRecord:
    return LambdaCapacityAttemptRecord(
        attempt_id=attempt_id,
        selected_shape=closeout.selected_shape or "gpu_1x_h100_pcie",
        selected_region=closeout.selected_region or "us-west-1",
        request_sent=closeout.launch_request_sent,
        response_received=closeout.status_code is not None,
        status_code=closeout.status_code,
        provider_error_message_redacted=closeout.provider_error_message_redacted,
        capacity_error_confirmed=closeout.capacity_error_confirmed,
        owned_instance_created=closeout.owned_instance_id_present,
        termination_required=closeout.termination_required,
        final_instance_count=closeout.final_instance_count,
        final_unmanaged_count=closeout.final_unmanaged_count,
        closeout_status=closeout.closeout_status,
    )


def load_lambda_capacity_history(path: str | Path) -> LambdaCapacityHistoryReport:
    return LambdaCapacityHistoryReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history(
    path: str | Path,
    report: LambdaCapacityHistoryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
