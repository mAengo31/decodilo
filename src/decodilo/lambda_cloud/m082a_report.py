"""Aggregate M082A optimizer smoke command and M083R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    load_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    load_lambda_diloco_optimizer_policy,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    load_lambda_m083r_diloco_optimizer_authorization,
)
from decodilo.lambda_cloud.m083r_diloco_optimizer_runbook_preview import (
    load_lambda_m083r_diloco_optimizer_runbook_preview,
)


class LambdaM082AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082A"
    report_passed: bool
    diloco_optimizer_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m083r_authorization_status: str
    runbook_preview_status: str
    optimizer_fidelity_status: str | None = None
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM082AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M082A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M082A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m082a_report_from_paths(
    *,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM082AReport:
    discovery = load_lambda_diloco_optimizer_command_discovery(command_discovery)
    optimizer_policy = load_lambda_diloco_optimizer_policy(policy)
    auth = load_lambda_m083r_diloco_optimizer_authorization(authorization)
    preview = load_lambda_m083r_diloco_optimizer_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_optimizer_command":
        blockers.append("diloco_optimizer_smoke_command_not_found")
    if discovery.expected_optimizer_fidelity != "optimizer_semantics_smoke":
        blockers.append("optimizer_semantics_smoke_not_expected")
    if optimizer_policy.policy_status != "policy_passed":
        blockers.append("diloco_optimizer_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m083r_diloco_optimizer_smoke":
        blockers.append("m083r_not_authorized")
    if preview.preview_status != "ready_for_future_m083r_diloco_optimizer_review":
        blockers.append("m083r_runbook_preview_not_ready")
    return LambdaM082AReport(
        report_passed=not blockers,
        diloco_optimizer_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=optimizer_policy.policy_status,
        m083r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        optimizer_fidelity_status=discovery.expected_optimizer_fidelity,
        inner_optimizer=discovery.inner_optimizer,
        outer_optimizer=discovery.outer_optimizer,
        blockers=blockers,
        warnings=["M082A is offline; M083R still requires fresh supervised approval"],
    )


def load_lambda_m082a_report(path: str | Path) -> LambdaM082AReport:
    return LambdaM082AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m082a_report(path: str | Path, report: LambdaM082AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
