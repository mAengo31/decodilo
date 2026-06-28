"""Aggregate M078A learner/syncer smoke command and M079R authorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    load_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_runbook_preview import (
    load_lambda_m079r_next_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    load_lambda_next_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.next_synthetic_experiment_policy import (
    load_lambda_next_synthetic_experiment_policy,
)


class LambdaM078AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M078A"
    report_passed: bool
    learner_syncer_smoke_command_added: bool
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m079r_authorization_status: str
    runbook_preview_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM078AReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M078A report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M078A report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m078a_report_from_paths(
    *,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM078AReport:
    discovery = load_lambda_next_synthetic_experiment_discovery(command_discovery)
    experiment_policy = load_lambda_next_synthetic_experiment_policy(policy)
    auth = load_lambda_m079r_next_synthetic_experiment_authorization(authorization)
    preview = load_lambda_m079r_next_synthetic_experiment_runbook_preview(
        runbook_preview
    )
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_next_synthetic_experiment_command":
        blockers.append("next_synthetic_experiment_command_not_found")
    if experiment_policy.policy_status != "policy_passed":
        blockers.append("next_synthetic_experiment_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m079r_next_synthetic_experiment":
        blockers.append("m079r_not_authorized")
    if (
        preview.preview_status
        != "ready_for_future_m079r_next_synthetic_experiment_review"
    ):
        blockers.append("m079r_runbook_preview_not_ready")
    return LambdaM078AReport(
        report_passed=not blockers,
        learner_syncer_smoke_command_added=not blockers,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=experiment_policy.policy_status,
        m079r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        blockers=blockers,
        warnings=["M078A is offline; M079R still requires fresh supervised approval"],
    )


def load_lambda_m078a_report(path: str | Path) -> LambdaM078AReport:
    return LambdaM078AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m078a_report(path: str | Path, report: LambdaM078AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
