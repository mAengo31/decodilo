from __future__ import annotations

from pathlib import Path

from lambda_fake_lifecycle_helpers import write_approved_m020

from decodilo.lambda_cloud.mutation_budget_lock import (
    build_lambda_mutation_budget_lock,
    write_lambda_mutation_budget_lock,
)
from decodilo.lambda_cloud.mutation_idempotency_plan import (
    build_lambda_mutation_idempotency_plan,
    write_lambda_mutation_idempotency_plan,
)
from decodilo.lambda_cloud.mutation_resource_scope import (
    build_lambda_mutation_resource_scope,
    write_lambda_mutation_resource_scope,
)
from decodilo.lambda_cloud.real_mutation_operation_spec import (
    build_lambda_real_mutation_operation_set,
    write_lambda_real_mutation_operation_set,
)


def write_m024_prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    _report, m020_path, approval_path = write_approved_m020(tmp_path)
    operation = build_lambda_real_mutation_operation_set()
    operation_path = tmp_path / "operation.json"
    write_lambda_real_mutation_operation_set(operation_path, operation)
    budget = build_lambda_mutation_budget_lock(
        m020_report=m020_path,
        approval_manifest_hash="approval-hash",
    )
    budget_path = tmp_path / "budget-lock.json"
    write_lambda_mutation_budget_lock(budget_path, budget)
    idempotency = build_lambda_mutation_idempotency_plan(
        run_id="run-example",
        operation="launch_one_instance",
        plan_hash="plan-hash",
    )
    idempotency_path = tmp_path / "idempotency.json"
    write_lambda_mutation_idempotency_plan(idempotency_path, idempotency)
    scope = build_lambda_mutation_resource_scope(m020_report=m020_path)
    scope_path = tmp_path / "scope.json"
    write_lambda_mutation_resource_scope(scope_path, scope)
    return {
        "m020": m020_path,
        "approval": approval_path,
        "operation": operation_path,
        "budget": budget_path,
        "idempotency": idempotency_path,
        "scope": scope_path,
    }
