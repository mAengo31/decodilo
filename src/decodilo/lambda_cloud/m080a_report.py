"""Aggregate M080A DiLoCo smoke command and M081R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    load_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    load_lambda_diloco_synthetic_policy,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    load_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_runbook_preview import (
    load_lambda_m081r_diloco_synthetic_runbook_preview,
)


class LambdaM080AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080A"
    report_passed: bool
    diloco_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m081r_authorization_status: str
    runbook_preview_status: str
    optimization_fidelity_required_to_be_honest: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM080AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M080A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M080A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m080a_report_from_paths(
    *,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM080AReport:
    discovery = load_lambda_diloco_synthetic_command_discovery(command_discovery)
    experiment_policy = load_lambda_diloco_synthetic_policy(policy)
    auth = load_lambda_m081r_diloco_synthetic_authorization(authorization)
    preview = load_lambda_m081r_diloco_synthetic_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_diloco_synthetic_command":
        blockers.append("diloco_synthetic_command_not_found")
    if experiment_policy.policy_status != "policy_passed":
        blockers.append("diloco_synthetic_policy_not_passed")
    if (
        auth.authorization_status
        != "authorized_for_future_m081r_diloco_synthetic_experiment"
    ):
        blockers.append("m081r_not_authorized")
    if preview.preview_status != "ready_for_future_m081r_diloco_synthetic_review":
        blockers.append("m081r_runbook_preview_not_ready")
    return LambdaM080AReport(
        report_passed=not blockers,
        diloco_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=experiment_policy.policy_status,
        m081r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        blockers=blockers,
        warnings=["M080A is offline; M081R still requires fresh supervised approval"],
    )


def load_lambda_m080a_report(path: str | Path) -> LambdaM080AReport:
    return LambdaM080AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m080a_report(path: str | Path, report: LambdaM080AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
