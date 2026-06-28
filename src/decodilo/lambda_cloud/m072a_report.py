"""Aggregate M072A tiny-smoke command and M073R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    load_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_runbook_preview import (
    load_lambda_m073r_tiny_smoke_runbook_preview,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    load_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    load_lambda_tiny_decodilo_smoke_policy,
)


class LambdaM072AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072A"
    report_passed: bool
    tiny_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m073r_authorization_status: str
    runbook_preview_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM072AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M072A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M072A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m072a_report_from_paths(
    *,
    smoke_discovery: str | Path,
    smoke_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM072AReport:
    discovery = load_lambda_tiny_decodilo_smoke_discovery(smoke_discovery)
    policy = load_lambda_tiny_decodilo_smoke_policy(smoke_policy)
    auth = load_lambda_m073r_tiny_smoke_authorization(authorization)
    preview = load_lambda_m073r_tiny_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if discovery.discovery_status not in {
        "found_safe_tiny_smoke_command",
        "safe_tiny_smoke_command_found",
    }:
        blockers.append("tiny_smoke_command_not_found")
    if policy.policy_status != "policy_passed":
        blockers.append("tiny_smoke_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m073r_tiny_decodilo_smoke":
        blockers.append("m073r_not_authorized")
    if preview.preview_status != "ready_for_future_m073r_tiny_smoke_review":
        blockers.append("m073r_runbook_preview_not_ready")
    return LambdaM072AReport(
        report_passed=not blockers,
        tiny_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=policy.policy_status,
        m073r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        blockers=blockers,
        warnings=["M072A is offline; M073R still requires fresh supervised approval"],
    )


def load_lambda_m072a_report(path: str | Path) -> LambdaM072AReport:
    return LambdaM072AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m072a_report(path: str | Path, report: LambdaM072AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
