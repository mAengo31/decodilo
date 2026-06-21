"""M027 fake-server-only minimal mutation execution policy."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)


class LambdaMinimalMutationExecutionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    require_m027_authorization: bool = True
    require_operation_spec: bool = True
    require_fake_server_only: bool = True
    require_endpoint_policy: bool = True
    require_mutation_guard: bool = True
    require_idempotency_plan: bool = True
    require_budget_lock: bool = True
    require_resource_scope: bool = True
    require_teardown_plan: bool = True
    require_termination_policy: bool = True
    require_approval_hash: bool = True
    max_instances: int = 1
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    real_execution_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False


class LambdaMinimalMutationPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    fake_execution_allowed: bool
    real_execution_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_minimal_mutation_execution_policy(
    *,
    context: LambdaMinimalMutationExecutionContext,
    m027_authorization_present: bool,
    operation_spec_present: bool,
    budget_lock_present: bool,
    idempotency_plan_present: bool,
    resource_scope_present: bool,
    teardown_plan_present: bool,
    termination_policy_present: bool,
    no_unmanaged_billable_resources: bool = True,
) -> LambdaMinimalMutationPolicyReport:
    blockers: list[str] = []
    if not m027_authorization_present:
        blockers.append("missing M027 authorization")
    if not operation_spec_present:
        blockers.append("missing operation spec")
    if not context.fake_execution_candidate:
        blockers.append("execution context is not fake_server_only")
    if not context.endpoint_policy_enabled:
        blockers.append("endpoint policy disabled")
    if not context.mutation_guard_enabled:
        blockers.append("mutation guard disabled")
    if not budget_lock_present:
        blockers.append("missing budget lock")
    if not idempotency_plan_present:
        blockers.append("missing idempotency plan")
    if not resource_scope_present:
        blockers.append("missing resource scope")
    if not teardown_plan_present:
        blockers.append("missing teardown plan")
    if not termination_policy_present:
        blockers.append("missing termination verification policy")
    if not no_unmanaged_billable_resources:
        blockers.append("unmanaged billable resources present")
    return LambdaMinimalMutationPolicyReport(
        fake_execution_allowed=not blockers,
        blockers=blockers,
        warnings=["M027 allows fake-server execution only; real execution remains forbidden."],
    )


def write_lambda_minimal_mutation_policy_report(
    path: str | Path,
    report: LambdaMinimalMutationPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
