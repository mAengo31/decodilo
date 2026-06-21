"""Second-launch attempt blocker after an M029 incident."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.m029_incident_report import (
    LambdaM029IncidentReport,
    load_lambda_m029_incident_report,
)


class LambdaM029SecondAttemptBlockerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    second_attempt_allowed: bool
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

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_second_attempt_blocker(
    incident: LambdaM029IncidentReport,
) -> LambdaM029SecondAttemptBlockerReport:
    allowed = incident.incident_status.startswith("closed_")
    blockers = [] if allowed else ["open_m029_incident_blocks_second_launch"]
    return LambdaM029SecondAttemptBlockerReport(
        second_attempt_allowed=allowed,
        blockers=blockers,
        current_incident_status=incident.incident_status,
    )


def build_lambda_m029_second_attempt_blocker_from_path(
    path: str | Path,
) -> LambdaM029SecondAttemptBlockerReport:
    return build_lambda_m029_second_attempt_blocker(load_lambda_m029_incident_report(path))


def write_lambda_m029_second_attempt_blocker(
    path: str | Path,
    report: LambdaM029SecondAttemptBlockerReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
