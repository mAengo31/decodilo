"""Parser for M027 fake-server minimal mutation responses."""

from __future__ import annotations

from typing import Any

from decodilo.lambda_cloud.minimal_mutation_result import (
    LambdaMinimalLaunchResult,
    LambdaMinimalTerminateResult,
)


def parse_minimal_mutation_response(
    payload: dict[str, Any],
) -> LambdaMinimalLaunchResult | LambdaMinimalTerminateResult:
    if payload.get("real_lambda_api_used"):
        raise ValueError("M027 parser rejects real Lambda API responses")
    if payload.get("billable_action_performed"):
        raise ValueError("M027 parser rejects billable action responses")
    if "data" in payload and payload.get("operation") is None:
        instance_ids = list((payload.get("data") or {}).get("instance_ids") or [])
        if len(instance_ids) == 1 and str(instance_ids[0]).startswith("fake-i-"):
            return LambdaMinimalLaunchResult(
                success=True,
                instance_id=str(instance_ids[0]),
                lifecycle_state="running",
                metadata={"strand_response_shape": True},
            )
    instance_id = str(payload.get("instance_id") or "")
    if not instance_id.startswith("fake-i-"):
        raise ValueError("M027 parser requires synthetic fake-i-* resource ids")
    operation = payload.get("operation")
    known = {
        "operation",
        "instance_id",
        "lifecycle_state",
        "idempotency_key",
        "fake_server_only",
        "real_lambda_api_used",
        "billable_action_performed",
        "termination_verified",
    }
    metadata = {key: value for key, value in payload.items() if key not in known}
    if operation == "launch_one_instance":
        return LambdaMinimalLaunchResult(
            success=True,
            instance_id=instance_id,
            lifecycle_state=str(payload.get("lifecycle_state") or "running"),
            idempotency_key=payload.get("idempotency_key"),
            metadata=metadata,
        )
    if operation == "terminate_owned_instance":
        return LambdaMinimalTerminateResult(
            success=True,
            instance_id=instance_id,
            lifecycle_state=str(payload.get("lifecycle_state") or "terminated"),
            idempotency_key=payload.get("idempotency_key"),
            termination_verified=bool(payload.get("termination_verified", False)),
            metadata=metadata,
        )
    raise ValueError(f"unsupported minimal mutation response operation: {operation}")
