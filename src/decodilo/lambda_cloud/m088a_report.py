"""Aggregate M088A bounded DiLoCo experiment command and M089R authorization."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    load_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    load_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    load_lambda_m089r_bounded_diloco_experiment_authorization,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_runbook_preview import (
    load_lambda_m089r_bounded_diloco_experiment_runbook_preview,
)


class LambdaM088AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088A"
    report_passed: bool
    bounded_diloco_experiment_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m089r_authorization_status: str
    runbook_preview_status: str
    bounded_experiment_status: str | None = None
    learners: int | None = None
    sync_rounds: int | None = None
    fragments: int | None = None
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    max_steps: int | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM088AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M088A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M088A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m088a_report_from_paths(
    *,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM088AReport:
    discovery = load_lambda_bounded_diloco_experiment_command_discovery(
        command_discovery
    )
    bounded_policy = load_lambda_bounded_diloco_experiment_policy(policy)
    auth = load_lambda_m089r_bounded_diloco_experiment_authorization(authorization)
    preview = load_lambda_m089r_bounded_diloco_experiment_runbook_preview(
        runbook_preview
    )
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_bounded_diloco_experiment_command":
        blockers.append("bounded_diloco_experiment_command_not_found")
    if bounded_policy.policy_status != "policy_passed":
        blockers.append("bounded_diloco_experiment_policy_not_passed")
    if (
        auth.authorization_status
        != "authorized_for_future_m089r_bounded_diloco_experiment"
    ):
        blockers.append("m089r_not_authorized")
    if (
        preview.preview_status
        != "ready_for_future_m089r_bounded_diloco_experiment_review"
    ):
        blockers.append("m089r_runbook_preview_not_ready")
    return LambdaM088AReport(
        report_passed=not blockers,
        bounded_diloco_experiment_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=bounded_policy.policy_status,
        m089r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        bounded_experiment_status=discovery.command_category,
        learners=discovery.learners,
        sync_rounds=discovery.sync_rounds,
        fragments=discovery.fragments,
        inner_optimizer=discovery.inner_optimizer,
        outer_optimizer=discovery.outer_optimizer,
        max_steps=discovery.max_steps,
        blockers=blockers,
        warnings=["M088A is offline; M089R still requires fresh supervised approval"],
    )


def load_lambda_m088a_report(path: str | Path) -> LambdaM088AReport:
    return LambdaM088AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m088a_report(path: str | Path, report: LambdaM088AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
