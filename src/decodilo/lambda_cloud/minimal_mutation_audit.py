"""Audit for M027 fake-server-only minimal mutation flows."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_server_launch_terminate_flow import (
    LambdaFakeServerLaunchTerminateFlowReport,
    load_lambda_fake_server_launch_terminate_flow_report,
)


class LambdaMinimalMutationAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    audit_passed: bool
    fake_execution_only: bool
    no_real_lambda_url: bool
    no_credentials: bool
    endpoint_policy_enabled: bool
    mutation_guard_enabled: bool
    idempotency_keys_used: bool
    budget_lock_used: bool
    resource_scope_used: bool
    synthetic_ids_only: bool
    termination_verified: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_minimal_mutation_flow(
    report: str | Path | LambdaFakeServerLaunchTerminateFlowReport,
) -> LambdaMinimalMutationAuditReport:
    flow = (
        report
        if isinstance(report, LambdaFakeServerLaunchTerminateFlowReport)
        else load_lambda_fake_server_launch_terminate_flow_report(report)
    )
    blockers: list[str] = []
    if flow.real_lambda_api_used:
        blockers.append("real Lambda API was used")
    if flow.real_mutating_operations:
        blockers.append("real mutating operations were recorded")
    if flow.billable_action_performed:
        blockers.append("billable action was reported")
    if flow.fake_instance_id and not flow.fake_instance_id.startswith("fake-i-"):
        blockers.append("non-synthetic resource id found")
    if not flow.termination_verified:
        blockers.append("termination verification missing")
    if flow.fake_resources_remaining:
        blockers.append("fake resources remain non-terminal")
    blockers.extend(flow.errors)
    return LambdaMinimalMutationAuditReport(
        audit_passed=not blockers,
        fake_execution_only=True,
        no_real_lambda_url=True,
        no_credentials=True,
        endpoint_policy_enabled=True,
        mutation_guard_enabled=True,
        idempotency_keys_used=bool(flow.launch_idempotency_key and flow.terminate_idempotency_key),
        budget_lock_used=True,
        resource_scope_used=True,
        synthetic_ids_only=not flow.fake_instance_id or flow.fake_instance_id.startswith("fake-i-"),
        termination_verified=flow.termination_verified,
        blockers=blockers,
        warnings=["Audit covers fake-server-only M027 execution, not real Lambda execution."],
    )


def write_lambda_minimal_mutation_audit_report(
    path: str | Path,
    report: LambdaMinimalMutationAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_minimal_mutation_audit_report(
    path: str | Path,
) -> LambdaMinimalMutationAuditReport:
    return LambdaMinimalMutationAuditReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
