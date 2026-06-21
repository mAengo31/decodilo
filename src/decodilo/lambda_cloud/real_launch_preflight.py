"""M029 launch preflight gate."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.future_launch_hold import LambdaFutureLaunchHoldReport
from decodilo.lambda_cloud.m029_incident_report import LambdaM029IncidentReport
from decodilo.lambda_cloud.m033_report import LambdaM033Report
from decodilo.lambda_cloud.m034_future_launch_hold import LambdaM034FutureLaunchHoldReport
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingReport


class LambdaM029LaunchPreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    preflight_passed: bool
    arming_passed: bool
    fake_server_mode: bool = False
    real_lambda_api_used: bool = False
    max_instances: int = 1
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    m033_third_attempt_authorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_m029_launch_preflight(
    *,
    arming_report: LambdaM029ArmingReport,
    previous_incident: LambdaM029IncidentReport | None = None,
    future_launch_hold: LambdaFutureLaunchHoldReport | None = None,
    m034_future_launch_hold: LambdaM034FutureLaunchHoldReport | None = None,
    m033_report: LambdaM033Report | None = None,
) -> LambdaM029LaunchPreflightReport:
    token = arming_report.token
    blockers = list(arming_report.blockers)
    if token is None:
        blockers.append("arming token missing")
    elif token.max_instances != 1 or token.max_budget > 50 or token.max_runtime_minutes > 30:
        blockers.append("arming token exceeds first-launch limits")
    if previous_incident is not None and not previous_incident.incident_status.startswith(
        "closed_"
    ):
        blockers.append("open_m029_incident_blocks_second_launch")
    if future_launch_hold is not None and future_launch_hold.future_launch_hold_active:
        blockers.append("future_launch_hold_active")
    if (
        m034_future_launch_hold is not None
        and m034_future_launch_hold.future_launch_hold_active
    ):
        blockers.append("m034_future_launch_hold_active")
    if m033_report is not None:
        if not m033_report.report_passed:
            blockers.append("m033_third_attempt_review_failed")
        if (
            m033_report.m034_authorization.status
            != "authorized_for_future_m034_third_launch_attempt"
        ):
            blockers.append("m034_third_attempt_authorization_missing")
        if m033_report.launch_ready or m033_report.launch_allowed:
            blockers.append("m033_report_attempted_to_enable_launch")
    return LambdaM029LaunchPreflightReport(
        run_id=arming_report.run_id,
        preflight_passed=not blockers,
        arming_passed=arming_report.arming_passed,
        fake_server_mode=bool(token and token.fake_server_mode),
        m033_third_attempt_authorized=bool(
            m033_report
            and m033_report.report_passed
            and m033_report.m034_authorization.status
            == "authorized_for_future_m034_third_launch_attempt"
        ),
        blockers=blockers,
        warnings=["M029 preflight does not permit restart/create/delete operations."],
    )


def write_lambda_m029_launch_preflight_report(
    path: str | Path,
    report: LambdaM029LaunchPreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
