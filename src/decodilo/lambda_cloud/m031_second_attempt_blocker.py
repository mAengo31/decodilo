"""Incident-local future launch blocker after an M031 response-loss incident."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m031_incident_report import (
    LambdaM031IncidentReport,
    load_lambda_m031_incident_report,
)


class LambdaM031SecondAttemptBlockerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_blocker_cleared: bool
    global_future_launch_blocked: bool = True
    blockers: list[str] = Field(default_factory=list)
    required_closeout_status: list[str] = Field(
        default_factory=lambda: [
            "closed_no_instance_visible",
            "closed_manual_termination_verified",
        ]
    )
    current_incident_status: str
    launch_ready: bool = False
    launch_allowed: bool = False

    @property
    def second_attempt_allowed(self) -> bool:
        return self.incident_blocker_cleared and not self.global_future_launch_blocked

    def to_json(self) -> str:
        payload = self.model_dump(mode="json")
        payload["second_attempt_allowed"] = self.second_attempt_allowed
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_lambda_m031_second_attempt_blocker(
    incident: LambdaM031IncidentReport,
) -> LambdaM031SecondAttemptBlockerReport:
    incident_cleared = incident.incident_status.startswith("closed_")
    blockers = [] if incident_cleared else ["open_m031_incident_blocks_future_launch"]
    blockers.append("repeated_response_loss_review_required")
    return LambdaM031SecondAttemptBlockerReport(
        incident_blocker_cleared=incident_cleared,
        global_future_launch_blocked=True,
        blockers=blockers,
        current_incident_status=incident.incident_status,
    )


def build_lambda_m031_second_attempt_blocker_from_path(
    path: str | Path,
) -> LambdaM031SecondAttemptBlockerReport:
    return build_lambda_m031_second_attempt_blocker(load_lambda_m031_incident_report(path))


def write_lambda_m031_second_attempt_blocker(
    path: str | Path,
    report: LambdaM031SecondAttemptBlockerReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
