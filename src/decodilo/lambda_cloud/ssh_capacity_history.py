"""Capacity and SSH-layer history for future SSH retry selection."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    LambdaSSHCapacityRetryCloseoutReport,
    load_lambda_ssh_capacity_retry_closeout,
)


class LambdaSSHCapacityHistoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_id: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    request_sent: bool = False
    response_received: bool = False
    status_code: int | None = None
    provider_error_message_redacted: str | None = None
    capacity_error_confirmed: bool = False
    owned_instance_created: bool = False
    ssh_attempted: bool = False
    ssh_failure_classification: str | None = None
    closeout_status: str | None = None


class LambdaSSHCapacityHistoryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    attempts: list[LambdaSSHCapacityHistoryRecord] = Field(default_factory=list)
    attempts_analyzed: int
    ssh_layer_failures_count: int
    capacity_rejections_count: int
    candidates_with_capacity_rejection: list[str] = Field(default_factory=list)
    candidates_with_ssh_auth_failure: list[str] = Field(default_factory=list)
    retry_same_candidate_region_recommended: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHCapacityHistoryReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.retry_same_candidate_region_recommended
        ):
            raise ValueError("SSH capacity history cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_capacity_history_from_paths(
    *,
    latest_closeout: str | Path,
    prior_m055b_report: str | Path | None = None,
) -> LambdaSSHCapacityHistoryReport:
    closeout = load_lambda_ssh_capacity_retry_closeout(latest_closeout)
    records = [_record_from_closeout("M055C", closeout)]
    prior_path = (
        Path(prior_m055b_report)
        if prior_m055b_report is not None
        else Path("/tmp/decodilo-lambda-m055b-report.json")
    )
    prior = _try_load_json(prior_path)
    if prior is not None:
        classification = prior.get("historical_probe_classification")
        if classification and classification not in {"success", "not_attempted"}:
            records.insert(
                0,
                LambdaSSHCapacityHistoryRecord(
                    attempt_id="M054B/M055A",
                    request_sent=True,
                    response_received=True,
                    capacity_error_confirmed=False,
                    owned_instance_created=True,
                    ssh_attempted=True,
                    ssh_failure_classification=str(classification),
                    closeout_status="ssh_layer_failure",
                ),
            )

    capacity_pairs = sorted(
        {
            _candidate_region(record)
            for record in records
            if record.capacity_error_confirmed and _candidate_region(record)
        }
    )
    ssh_failures = sorted(
        {
            record.ssh_failure_classification or "unknown_ssh_failure"
            for record in records
            if record.ssh_attempted and record.ssh_failure_classification
        }
    )
    return LambdaSSHCapacityHistoryReport(
        attempts=records,
        attempts_analyzed=len(records),
        ssh_layer_failures_count=len(ssh_failures),
        capacity_rejections_count=sum(1 for record in records if record.capacity_error_confirmed),
        candidates_with_capacity_rejection=capacity_pairs,
        candidates_with_ssh_auth_failure=ssh_failures,
        warnings=[
            "same candidate/region retry is not recommended by default",
            "capacity history is offline evidence and performs no Lambda calls",
        ],
    )


def _record_from_closeout(
    attempt_id: str,
    closeout: LambdaSSHCapacityRetryCloseoutReport,
) -> LambdaSSHCapacityHistoryRecord:
    return LambdaSSHCapacityHistoryRecord(
        attempt_id=attempt_id,
        selected_candidate=closeout.selected_candidate,
        selected_region=closeout.selected_region,
        request_sent=closeout.launch_request_sent,
        response_received=closeout.launch_response_received,
        status_code=closeout.status_code,
        provider_error_message_redacted=closeout.provider_error_message_redacted,
        capacity_error_confirmed=closeout.capacity_error_confirmed,
        owned_instance_created=closeout.owned_instance_id_present,
        ssh_attempted=closeout.ssh_attempted,
        closeout_status=closeout.closeout_status,
    )


def _candidate_region(record: LambdaSSHCapacityHistoryRecord) -> str | None:
    if record.selected_candidate is None or record.selected_region is None:
        return None
    return f"{record.selected_candidate}/{record.selected_region}"


def load_lambda_ssh_capacity_history(path: str | Path) -> LambdaSSHCapacityHistoryReport:
    return LambdaSSHCapacityHistoryReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_capacity_history(
    path: str | Path,
    report: LambdaSSHCapacityHistoryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _try_load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
