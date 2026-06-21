"""End-to-end fake-server launch/terminate flow for M027."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_server_failure_modes import (
    LambdaMinimalFakeFailure,
    LambdaMinimalFakeFailureMode,
)
from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)
from decodilo.lambda_cloud.minimal_mutation_executor import LambdaMinimalMutationExecutor
from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
)


class LambdaFakeServerLaunchTerminateFlowReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    fake_launch_executed: bool
    fake_terminate_executed: bool
    fake_instance_id: str | None = None
    launch_idempotency_key: str
    terminate_idempotency_key: str
    duplicate_launch_safe: bool
    duplicate_terminate_safe: bool
    termination_verified: bool
    fake_resources_remaining: list[str] = Field(default_factory=list)
    recoverable_failures: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def run_fake_server_launch_terminate_flow(
    *,
    context: LambdaMinimalMutationExecutionContext,
    launch_failure_mode: LambdaMinimalFakeFailureMode = "none",
    terminate_failure_mode: LambdaMinimalFakeFailureMode = "none",
) -> LambdaFakeServerLaunchTerminateFlowReport:
    executor = LambdaMinimalMutationExecutor(context=context)
    launch_key = "idem-m027-fake-launch"
    terminate_key = "idem-m027-fake-terminate"
    launch_request = LambdaMinimalLaunchOneInstanceRequest(
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        idempotency_key=launch_key,
        dry_run_plan_hash=context.operation_spec_hash,
        budget_lock_hash=context.budget_lock_hash,
        approval_manifest_hash=context.approval_manifest_hash,
        resource_ledger_hash=context.resource_scope_hash,
        teardown_plan_hash=context.teardown_plan_hash,
    )
    recoverable: list[str] = []
    errors: list[str] = []
    try:
        launch_result = executor.execute_launch(
            launch_request,
            failure_mode=launch_failure_mode,
        )
        instance_id = launch_result.instance_id
    except LambdaMinimalFakeFailure as exc:
        recoverable.append(exc.mode)
        resources = executor.transport.registry.list_resources()
        instance_id = resources[0].instance_id if resources else None
    if instance_id is None:
        errors.append("fake launch did not create recoverable instance")
        instance_id = ""
    duplicate_launch = executor.transport.registry.launch(
        instance_type=launch_request.instance_type,
        region=launch_request.region,
        idempotency_key=launch_key,
    )
    terminate_request = LambdaMinimalTerminateOwnedInstanceRequest(
        owned_instance_id=instance_id,
        idempotency_key=terminate_key,
        resource_scope_hash=context.resource_scope_hash,
        ledger_hash=context.resource_scope_hash,
        termination_verification_policy_hash="termination-policy-hash",
    )
    termination_verified = False
    try:
        terminate_result = executor.execute_terminate(
            terminate_request,
            failure_mode=terminate_failure_mode,
        )
        termination_verified = terminate_result.termination_verified
    except LambdaMinimalFakeFailure as exc:
        recoverable.append(exc.mode)
        resource = executor.transport.registry.get(instance_id)
        termination_verified = bool(resource and resource.lifecycle_state == "terminated")
    duplicate_terminate = executor.transport.registry.terminate(
        instance_id=instance_id,
        idempotency_key=terminate_key,
    )
    remaining = [
        resource.instance_id
        for resource in executor.transport.registry.list_resources()
        if resource.lifecycle_state != "terminated"
    ]
    if not termination_verified:
        errors.append("fake termination was not verified")
    return LambdaFakeServerLaunchTerminateFlowReport(
        fake_launch_executed=bool(instance_id),
        fake_terminate_executed=termination_verified,
        fake_instance_id=instance_id,
        launch_idempotency_key=launch_key,
        terminate_idempotency_key=terminate_key,
        duplicate_launch_safe=duplicate_launch.instance_id == instance_id,
        duplicate_terminate_safe=duplicate_terminate.lifecycle_state == "terminated",
        termination_verified=termination_verified,
        fake_resources_remaining=remaining,
        recoverable_failures=recoverable,
        errors=errors,
    )


def write_lambda_fake_server_launch_terminate_flow_report(
    path: str | Path,
    report: LambdaFakeServerLaunchTerminateFlowReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_fake_server_launch_terminate_flow_report(
    path: str | Path,
) -> LambdaFakeServerLaunchTerminateFlowReport:
    return LambdaFakeServerLaunchTerminateFlowReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
