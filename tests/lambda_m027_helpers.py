from __future__ import annotations

from pathlib import Path

from lambda_m026_helpers import write_m026_core_artifacts

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    build_fake_server_execution_context,
)
from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
)


def write_m027_core_artifacts(tmp_path: Path) -> dict[str, Path]:
    paths = write_m026_core_artifacts(tmp_path)
    teardown = tmp_path / "teardown-plan.json"
    teardown.write_text('{"teardown_enabled": false, "live_resource_ids": []}\n', encoding="utf-8")
    return {**paths, "teardown": teardown}


def fake_context():
    return build_fake_server_execution_context()


def fake_launch_request(idempotency_key: str = "idem-launch"):
    return LambdaMinimalLaunchOneInstanceRequest(
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        idempotency_key=idempotency_key,
        dry_run_plan_hash="plan",
        budget_lock_hash="budget",
        approval_manifest_hash="approval",
        resource_ledger_hash="ledger",
        teardown_plan_hash="teardown",
    )


def fake_terminate_request(instance_id: str, idempotency_key: str = "idem-terminate"):
    return LambdaMinimalTerminateOwnedInstanceRequest(
        owned_instance_id=instance_id,
        idempotency_key=idempotency_key,
        resource_scope_hash="scope",
        ledger_hash="ledger",
        termination_verification_policy_hash="termination",
    )
