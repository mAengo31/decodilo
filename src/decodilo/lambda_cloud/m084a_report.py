"""Aggregate M084A integrated DiLoCo smoke command and M085R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    load_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    load_lambda_integrated_diloco_policy,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    load_lambda_m085r_integrated_diloco_authorization,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_runbook_preview import (
    load_lambda_m085r_integrated_diloco_runbook_preview,
)


class LambdaM084AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084A"
    report_passed: bool
    integrated_diloco_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m085r_authorization_status: str
    runbook_preview_status: str
    integrated_fidelity_status: str | None = None
    learners: int | None = None
    sync_rounds: int | None = None
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM084AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M084A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M084A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m084a_report_from_paths(
    *,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM084AReport:
    discovery = load_lambda_integrated_diloco_command_discovery(command_discovery)
    integrated_policy = load_lambda_integrated_diloco_policy(policy)
    auth = load_lambda_m085r_integrated_diloco_authorization(authorization)
    preview = load_lambda_m085r_integrated_diloco_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_integrated_diloco_command":
        blockers.append("integrated_diloco_smoke_command_not_found")
    if (
        discovery.expected_integrated_fidelity
        != "integrated_optimizer_protocol_smoke"
    ):
        blockers.append("integrated_optimizer_protocol_smoke_not_expected")
    if integrated_policy.policy_status != "policy_passed":
        blockers.append("integrated_diloco_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m085r_integrated_diloco_smoke":
        blockers.append("m085r_not_authorized")
    if preview.preview_status != "ready_for_future_m085r_integrated_diloco_review":
        blockers.append("m085r_runbook_preview_not_ready")
    return LambdaM084AReport(
        report_passed=not blockers,
        integrated_diloco_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=integrated_policy.policy_status,
        m085r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        integrated_fidelity_status=discovery.expected_integrated_fidelity,
        learners=discovery.learners,
        sync_rounds=discovery.sync_rounds,
        inner_optimizer=discovery.inner_optimizer,
        outer_optimizer=discovery.outer_optimizer,
        blockers=blockers,
        warnings=["M084A is offline; M085R still requires fresh supervised approval"],
    )


def load_lambda_m084a_report(path: str | Path) -> LambdaM084AReport:
    return LambdaM084AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m084a_report(path: str | Path, report: LambdaM084AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
