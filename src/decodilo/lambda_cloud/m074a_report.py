"""Aggregate M074A runtime/protocol smoke command and M075R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    load_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_runbook_preview import (
    load_lambda_m075r_runtime_protocol_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    load_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    load_lambda_runtime_protocol_smoke_policy,
)


class LambdaM074AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074A"
    report_passed: bool
    runtime_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m075r_authorization_status: str
    runbook_preview_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM074AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M074A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M074A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m074a_report_from_paths(
    *,
    runtime_discovery: str | Path,
    runtime_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM074AReport:
    discovery = load_lambda_runtime_protocol_smoke_discovery(runtime_discovery)
    policy = load_lambda_runtime_protocol_smoke_policy(runtime_policy)
    auth = load_lambda_m075r_runtime_protocol_smoke_authorization(authorization)
    preview = load_lambda_m075r_runtime_protocol_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_runtime_protocol_smoke_command":
        blockers.append("runtime_protocol_smoke_command_not_found")
    if policy.policy_status != "policy_passed":
        blockers.append("runtime_protocol_smoke_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m075r_runtime_protocol_smoke":
        blockers.append("m075r_not_authorized")
    if preview.preview_status != "ready_for_future_m075r_runtime_protocol_smoke_review":
        blockers.append("m075r_runbook_preview_not_ready")
    return LambdaM074AReport(
        report_passed=not blockers,
        runtime_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=policy.policy_status,
        m075r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        blockers=blockers,
        warnings=["M074A is offline; M075R still requires fresh supervised approval"],
    )


def load_lambda_m074a_report(path: str | Path) -> LambdaM074AReport:
    return LambdaM074AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m074a_report(path: str | Path, report: LambdaM074AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
