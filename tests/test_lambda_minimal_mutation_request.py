import pytest
from lambda_m027_helpers import fake_launch_request, fake_terminate_request
from pydantic import ValidationError

from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
    prepare_minimal_launch_request,
    prepare_minimal_terminate_request,
)


def test_valid_fake_launch_request_serializes():
    request = fake_launch_request()
    prepared = prepare_minimal_launch_request(request)

    assert request.operation == "launch_one_instance"
    assert prepared.fake_server_only is True
    assert prepared.real_lambda_request_allowed is False
    assert prepared.launch_allowed is False


def test_missing_idempotency_key_rejected():
    with pytest.raises(ValidationError):
        LambdaMinimalLaunchOneInstanceRequest(
            instance_type="gpu_8x_h100_sxm",
            region="us-west-1",
            idempotency_key="",
            dry_run_plan_hash="plan",
            budget_lock_hash="budget",
            approval_manifest_hash="approval",
            resource_ledger_hash="ledger",
            teardown_plan_hash="teardown",
        )


def test_valid_fake_terminate_request_serializes():
    request = fake_terminate_request("fake-i-123")
    prepared = prepare_minimal_terminate_request(request)

    assert request.operation == "terminate_owned_instance"
    assert prepared.future_endpoint_template == "/instance-operations/terminate"
    assert prepared.future_http_method == "POST"
    assert prepared.real_lambda_request_allowed is False


def test_unowned_terminate_rejected():
    with pytest.raises(ValidationError):
        LambdaMinimalTerminateOwnedInstanceRequest(
            owned_instance_id="live-instance-id",
            idempotency_key="idem",
            resource_scope_hash="scope",
            ledger_hash="ledger",
            termination_verification_policy_hash="termination",
        )


def test_real_lambda_request_allowed_true_rejected():
    with pytest.raises(ValidationError):
        LambdaMinimalLaunchOneInstanceRequest(
            instance_type="gpu_8x_h100_sxm",
            region="us-west-1",
            idempotency_key="idem",
            dry_run_plan_hash="plan",
            budget_lock_hash="budget",
            approval_manifest_hash="approval",
            resource_ledger_hash="ledger",
            teardown_plan_hash="teardown",
            real_lambda_request_allowed=True,
        )
