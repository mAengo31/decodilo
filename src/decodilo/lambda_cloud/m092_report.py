"""Aggregate M092 tiny real-training smoke planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m093r_tiny_real_training_authorization import (
    load_lambda_m093r_tiny_real_training_authorization,
)
from decodilo.lambda_cloud.m093r_tiny_real_training_runbook_preview import (
    load_lambda_m093r_tiny_real_training_runbook_preview,
)
from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    load_lambda_tiny_real_training_command_discovery,
)
from decodilo.lambda_cloud.tiny_real_training_policy import (
    load_lambda_tiny_real_training_policy,
)
from decodilo.lambda_cloud.tiny_real_training_readiness import (
    load_lambda_tiny_real_training_readiness,
)


class LambdaM092Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    report_passed: bool
    readiness_status: str
    discovery_status: str
    selected_command: list[str] = Field(default_factory=list)
    policy_status: str
    m093r_authorization_status: str
    runbook_preview_status: str
    tiny_real_training_command_added: bool
    real_training_mechanics_exercised: bool
    torch_required: bool
    gpu_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM092Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M092 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M092 report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m092_report_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM092Report:
    ready = load_lambda_tiny_real_training_readiness(readiness)
    discovery = load_lambda_tiny_real_training_command_discovery(command_discovery)
    training_policy = load_lambda_tiny_real_training_policy(policy)
    auth = load_lambda_m093r_tiny_real_training_authorization(authorization)
    preview = load_lambda_m093r_tiny_real_training_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if ready.readiness_status != "ready_for_future_tiny_real_training_planning":
        blockers.append("tiny_real_training_readiness_not_ready")
    if discovery.discovery_status != "found_safe_tiny_real_training_command":
        blockers.append("tiny_real_training_command_not_found")
    if training_policy.policy_status != "policy_passed":
        blockers.append("tiny_real_training_policy_not_passed")
    if (
        auth.authorization_status
        != "authorized_for_future_m093r_tiny_real_training_smoke"
    ):
        blockers.append("m093r_not_authorized")
    if preview.preview_status != "ready_for_future_m093r_tiny_real_training_review":
        blockers.append("m093r_runbook_preview_not_ready")
    return LambdaM092Report(
        report_passed=not blockers,
        readiness_status=ready.readiness_status,
        discovery_status=discovery.discovery_status,
        selected_command=discovery.argv_tokens,
        policy_status=training_policy.policy_status,
        m093r_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        tiny_real_training_command_added=not blockers,
        real_training_mechanics_exercised=discovery.real_training_mechanics_exercised,
        torch_required=discovery.torch_required,
        gpu_required=discovery.gpu_required,
        blockers=blockers,
        warnings=[
            "M092 is offline; M093R still requires fresh supervised approval",
        ],
    )


def load_lambda_m092_report(path: str | Path) -> LambdaM092Report:
    return LambdaM092Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m092_report(path: str | Path, report: LambdaM092Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
