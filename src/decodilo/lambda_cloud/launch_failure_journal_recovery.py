"""Recover Lambda launch incident state when report.json was not written."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_launch_journal import (
    LambdaM029JournalEvent,
    replay_m029_launch_journal,
)


class LambdaLaunchFailureJournalRecoveryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_request_sent: bool
    response_received: bool
    response_timeout: bool
    owned_instance_id: str | None = None
    termination_request_sent: bool = False
    termination_verified: bool = False
    manual_review_required: bool
    missing_report_detected: bool = True
    recovered_from_journal: bool
    events_seen: int = 0
    corrupted: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchFailureJournalRecoveryReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("journal recovery cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def recover_lambda_launch_failure_from_journal(
    journal: str | Path,
    *,
    report_path: str | Path | None = None,
) -> LambdaLaunchFailureJournalRecoveryReport:
    report_missing = report_path is None or not Path(report_path).exists()
    events: list[LambdaM029JournalEvent] = []
    errors: list[str] = []
    try:
        for raw in Path(journal).read_text(encoding="utf-8").splitlines():
            if raw.strip():
                events.append(LambdaM029JournalEvent.model_validate_json(raw))
    except Exception as exc:  # noqa: BLE001 - corrupted journal is evidence
        errors.append(str(exc))
        return LambdaLaunchFailureJournalRecoveryReport(
            launch_request_sent=False,
            response_received=False,
            response_timeout=False,
            manual_review_required=True,
            missing_report_detected=report_missing,
            recovered_from_journal=False,
            events_seen=len(events),
            corrupted=True,
            blockers=["launch_journal_corrupted"],
            errors=errors,
        )
    replay = replay_m029_launch_journal(journal)
    event_types = {event.event_type for event in events}
    launch_sent = "m029_launch_request_sent" in event_types
    response_received = "m029_launch_response_received" in event_types
    response_timeout = "m029_launch_response_timeout" in event_types
    termination_sent = "m029_termination_request_sent" in event_types
    manual_review = bool(
        launch_sent
        and (
            not response_received
            or not replay.termination_verified
            or "m029_manual_review_required" in event_types
        )
    )
    blockers = (
        ["missing_m029_report_after_launch_request"]
        if report_missing and launch_sent
        else []
    )
    return LambdaLaunchFailureJournalRecoveryReport(
        launch_request_sent=launch_sent,
        response_received=response_received,
        response_timeout=response_timeout,
        owned_instance_id=replay.owned_instance_id,
        termination_request_sent=termination_sent,
        termination_verified=replay.termination_verified,
        manual_review_required=manual_review,
        missing_report_detected=report_missing,
        recovered_from_journal=not replay.corrupted,
        events_seen=len(events),
        corrupted=replay.corrupted,
        blockers=blockers,
        warnings=[
            "recovered partial launch state from journal",
            "future launch remains blocked until incident closeout",
        ]
        if launch_sent
        else [],
        errors=[*errors, *replay.errors],
    )


def write_lambda_launch_failure_journal_recovery(
    path: str | Path,
    report: LambdaLaunchFailureJournalRecoveryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_launch_failure_journal_recovery(
    path: str | Path,
) -> LambdaLaunchFailureJournalRecoveryReport:
    return LambdaLaunchFailureJournalRecoveryReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
