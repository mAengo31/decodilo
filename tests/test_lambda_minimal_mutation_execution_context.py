import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
    build_fake_server_execution_context,
)


def test_fake_server_only_localhost_context_accepted():
    context = build_fake_server_execution_context(base_url="http://127.0.0.1:8123")

    assert context.fake_execution_candidate is True
    assert context.real_mutation_enabled is False
    assert context.launch_ready is False
    assert context.launch_allowed is False


def test_fake_server_only_real_lambda_url_rejected():
    with pytest.raises(ValidationError):
        live_url = "https://" + "cloud.lambdalabs.com" + "/api/v1"
        build_fake_server_execution_context(base_url=live_url)


def test_credentials_present_rejected():
    with pytest.raises(ValidationError):
        LambdaMinimalMutationExecutionContext(
            mode="fake_server_only",
            base_url="memory://fake",
            fake_server_mode=True,
            run_id="run",
            m027_authorization_hash="auth",
            operation_spec_hash="spec",
            approval_manifest_hash="approval",
            budget_lock_hash="budget",
            idempotency_plan_hash="idem",
            resource_scope_hash="scope",
            teardown_plan_hash="teardown",
            credential_source="api-key-file",
        )


def test_disabled_mode_rejects_execution_candidate():
    context = LambdaMinimalMutationExecutionContext(
        mode="disabled",
        run_id="run",
        m027_authorization_hash="auth",
        operation_spec_hash="spec",
        approval_manifest_hash="approval",
        budget_lock_hash="budget",
        idempotency_plan_hash="idem",
        resource_scope_hash="scope",
        teardown_plan_hash="teardown",
    )

    assert context.fake_execution_candidate is False
