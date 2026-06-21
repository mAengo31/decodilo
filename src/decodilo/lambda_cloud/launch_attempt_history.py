"""M035 launch-attempt history after three ambiguous real attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m034_incident_report import (
    LambdaM034IncidentReport,
    load_lambda_m034_incident_report,
)

LambdaLaunchAttemptMilestone = Literal["M029C", "M031", "M034C"]


class LambdaLaunchAttemptRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_id: str
    milestone: LambdaLaunchAttemptMilestone
    launch_request_sent: bool
    launch_response_received: bool
    owned_instance_id_present: bool
    termination_request_sent: bool
    termination_verified: bool
    manual_review_required: bool
    estimated_spend: float | None = None
    post_discovery_instance_count: int | None = None
    console_confirmation_status: str = "not_recorded_in_attempt_report"
    incident_status: str
    diagnostics_persisted: bool = False
    response_capture_available: bool = False
    root_cause_category: str = "unknown"
    lessons_learned: list[str] = Field(default_factory=list)


class LambdaLaunchAttemptHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempts: list[LambdaLaunchAttemptRecord]

    @property
    def response_loss_count(self) -> int:
        return sum(
            int(record.launch_request_sent and not record.launch_response_received)
            for record in self.attempts
        )

    @property
    def repeated_response_loss_detected(self) -> bool:
        return self.response_loss_count >= 2

    @property
    def all_incidents_closed(self) -> bool:
        return all(record.incident_status.startswith("closed_") for record in self.attempts)


class LambdaLaunchAttemptHistoryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    history: LambdaLaunchAttemptHistory
    attempts_represented: int
    response_loss_count: int
    repeated_response_loss_detected: bool
    all_incidents_closed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLaunchAttemptHistoryReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 attempt history cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_attempt_record_from_m029_report(
    report: LambdaM029Report,
    *,
    attempt_id: str,
    milestone: LambdaLaunchAttemptMilestone,
    incident_status: str = "closed_no_instance_visible",
    console_confirmation_status: str = "confirmed_no_visible_instances",
    post_discovery_instance_count: int | None = 0,
    diagnostics_persisted: bool | None = None,
) -> LambdaLaunchAttemptRecord:
    response_capture_available = bool(
        report.launch_response_http_status is not None
        or report.launch_response_classification is not None
    )
    persisted = (
        response_capture_available if diagnostics_persisted is None else diagnostics_persisted
    )
    response_lost = report.launch_request_sent and not report.launch_response_received
    return LambdaLaunchAttemptRecord(
        attempt_id=attempt_id,
        milestone=milestone,
        launch_request_sent=report.launch_request_sent,
        launch_response_received=report.launch_response_received,
        owned_instance_id_present=bool(report.owned_instance_id_redacted),
        termination_request_sent=report.termination_request_sent,
        termination_verified=report.termination_verified,
        manual_review_required=report.manual_review_required,
        estimated_spend=report.estimated_spend,
        post_discovery_instance_count=post_discovery_instance_count,
        console_confirmation_status=console_confirmation_status,
        incident_status=incident_status,
        diagnostics_persisted=persisted,
        response_capture_available=response_capture_available,
        root_cause_category="response_loss" if response_lost else "not_response_loss",
        lessons_learned=[
            "launch response was lost; no automatic retry is allowed",
            "owned instance ID was not recorded; automated termination stayed blocked",
        ]
        if response_lost
        else ["attempt did not match response-loss pattern"],
    )


def build_lambda_launch_attempt_record_from_m034_incident(
    incident: LambdaM034IncidentReport,
) -> LambdaLaunchAttemptRecord:
    post_count = incident.post_discovery_summary.get("post_instance_count")
    return LambdaLaunchAttemptRecord(
        attempt_id="m034c",
        milestone="M034C",
        launch_request_sent=incident.launch_request_sent,
        launch_response_received=incident.launch_response_received,
        owned_instance_id_present=incident.owned_instance_id_present,
        termination_request_sent=incident.termination_request_sent,
        termination_verified=incident.termination_verified,
        manual_review_required=incident.manual_review_required,
        estimated_spend=incident.estimated_spend,
        post_discovery_instance_count=post_count if isinstance(post_count, int) else None,
        console_confirmation_status=incident.console_confirmation.confirmation_status,
        incident_status=incident.incident_status,
        diagnostics_persisted=incident.transport_error_persisted,
        response_capture_available=incident.response_capture_persisted,
        root_cause_category=incident.transport_error_type or "response_loss_transport_error",
        lessons_learned=[
            "historical M034C transport diagnostics were not persisted",
            "crash-safe diagnostics must wrap future mutation attempts",
        ],
    )


def build_lambda_launch_attempt_history_report(
    *,
    m029c_report: LambdaM029Report,
    m031_report: LambdaM029Report,
    m034_incident: LambdaM034IncidentReport,
) -> LambdaLaunchAttemptHistoryReport:
    records = [
        build_lambda_launch_attempt_record_from_m029_report(
            m029c_report,
            attempt_id="m029c",
            milestone="M029C",
        ),
        build_lambda_launch_attempt_record_from_m029_report(
            m031_report,
            attempt_id="m031",
            milestone="M031",
        ),
        build_lambda_launch_attempt_record_from_m034_incident(m034_incident),
    ]
    history = LambdaLaunchAttemptHistory(attempts=records)
    blockers: list[str] = []
    if len(records) != 3:
        blockers.append("expected_three_attempts_missing")
    if not history.all_incidents_closed:
        blockers.append("one_or_more_incidents_not_closed")
    return LambdaLaunchAttemptHistoryReport(
        history=history,
        attempts_represented=len(records),
        response_loss_count=history.response_loss_count,
        repeated_response_loss_detected=history.repeated_response_loss_detected,
        all_incidents_closed=history.all_incidents_closed,
        blockers=blockers,
        warnings=[
            "three real launch attempts produced no owned instance ID",
            "M034C historical diagnostics remain incomplete but incident is closed",
        ],
    )


def build_lambda_launch_attempt_history_report_from_paths(
    *,
    m029_report: str | Path,
    m031_report: str | Path,
    m034_recovery: str | Path,
) -> LambdaLaunchAttemptHistoryReport:
    return build_lambda_launch_attempt_history_report(
        m029c_report=load_lambda_m029_report(m029_report),
        m031_report=load_lambda_m029_report(m031_report),
        m034_incident=load_lambda_m034_incident_report(m034_recovery),
    )


def load_lambda_launch_attempt_history_report(
    path: str | Path,
) -> LambdaLaunchAttemptHistoryReport:
    return LambdaLaunchAttemptHistoryReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_attempt_history_report(
    path: str | Path,
    report: LambdaLaunchAttemptHistoryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
