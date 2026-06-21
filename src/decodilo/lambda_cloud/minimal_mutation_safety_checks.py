"""Safety checks for the M027 minimal fake-server mutation path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)


class LambdaMinimalMutationSafetyCheckReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    safety_checks_passed: bool
    real_url_blocked: bool
    credentials_blocked: bool
    fake_server_only: bool
    endpoint_policy_enabled: bool
    mutation_guard_enabled: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_execution_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_minimal_mutation_safety_checks(
    context: LambdaMinimalMutationExecutionContext,
) -> LambdaMinimalMutationSafetyCheckReport:
    blockers: list[str] = []
    if not context.fake_execution_candidate:
        blockers.append("context is not fake-server-only")
    if context.credential_source:
        blockers.append("credentials are forbidden")
    if not context.endpoint_policy_enabled:
        blockers.append("endpoint policy is required")
    if not context.mutation_guard_enabled:
        blockers.append("mutation guard is required")
    return LambdaMinimalMutationSafetyCheckReport(
        safety_checks_passed=not blockers,
        real_url_blocked=True,
        credentials_blocked=True,
        fake_server_only=context.fake_execution_candidate,
        endpoint_policy_enabled=context.endpoint_policy_enabled,
        mutation_guard_enabled=context.mutation_guard_enabled,
        blockers=blockers,
        warnings=["Safety checks do not enable real Lambda mutation."],
    )


def write_lambda_minimal_mutation_safety_report(
    path: str | Path,
    report: LambdaMinimalMutationSafetyCheckReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
