"""In-memory fake transport for M027 minimal launch/terminate execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from decodilo.lambda_cloud.fake_server_failure_modes import (
    LambdaMinimalFakeFailure,
    LambdaMinimalFakeFailureMode,
)
from decodilo.lambda_cloud.fake_server_resource_registry import (
    LambdaFakeServerResourceRegistry,
)
from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
)


@dataclass
class LambdaMinimalMutationFakeTransport:
    registry: LambdaFakeServerResourceRegistry = field(
        default_factory=LambdaFakeServerResourceRegistry
    )
    base_url: str = "memory://lambda-minimal-fake-server"
    fake_server_mode: bool = True
    credential_source: str | None = None
    fake_mutating_operations: int = 0
    real_mutating_operations: int = 0
    billable_action_performed: bool = False

    def __post_init__(self) -> None:
        if not self.fake_server_mode:
            raise ValueError("minimal mutation fake transport requires fake_server_mode")
        if self.credential_source:
            raise ValueError("minimal mutation fake transport rejects credentials")
        if "lambdalabs.com" in self.base_url.lower() or "lambda.ai" in self.base_url.lower():
            raise ValueError("minimal mutation fake transport rejects real Lambda URLs")

    def launch_one_instance(
        self,
        request: LambdaMinimalLaunchOneInstanceRequest,
        *,
        failure_mode: LambdaMinimalFakeFailureMode = "none",
    ) -> dict:
        resource = self.registry.launch(
            instance_type=request.instance_type,
            region=request.region,
            idempotency_key=request.idempotency_key,
        )
        self.fake_mutating_operations += 1
        if failure_mode in {"launch_response_lost", "launch_timeout_but_created"}:
            raise LambdaMinimalFakeFailure(failure_mode, "fake launch response unavailable")
        if failure_mode == "malformed_launch_response":
            return {"operation": "launch_one_instance", "instance_id": "malformed-live-id"}
        return {
            "operation": "launch_one_instance",
            "instance_id": resource.instance_id,
            "lifecycle_state": resource.lifecycle_state,
            "idempotency_key": request.idempotency_key,
            "fake_server_only": True,
            "real_lambda_api_used": False,
            "billable_action_performed": False,
        }

    def terminate_owned_instance(
        self,
        request: LambdaMinimalTerminateOwnedInstanceRequest,
        *,
        failure_mode: LambdaMinimalFakeFailureMode = "none",
    ) -> dict:
        resource = self.registry.terminate(
            instance_id=request.owned_instance_id,
            idempotency_key=request.idempotency_key,
        )
        self.fake_mutating_operations += 1
        if failure_mode in {"terminate_response_lost", "terminate_timeout_but_terminated"}:
            raise LambdaMinimalFakeFailure(failure_mode, "fake terminate response unavailable")
        if failure_mode == "malformed_terminate_response":
            return {"operation": "terminate_owned_instance", "instance_id": "live-id"}
        return {
            "operation": "terminate_owned_instance",
            "instance_id": resource.instance_id,
            "lifecycle_state": resource.lifecycle_state,
            "idempotency_key": request.idempotency_key,
            "termination_verified": resource.lifecycle_state == "terminated",
            "fake_server_only": True,
            "real_lambda_api_used": False,
            "billable_action_performed": False,
        }
