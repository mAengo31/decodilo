from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)
from decodilo.lambda_cloud.minimal_mutation_safety_checks import (
    run_minimal_mutation_safety_checks,
)


def test_safety_checks_pass_fake_context():
    report = run_minimal_mutation_safety_checks(fake_context())

    assert report.safety_checks_passed is True
    assert report.real_execution_allowed is False
    assert report.launch_allowed is False


def test_disabled_context_blocks_safety():
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
    report = run_minimal_mutation_safety_checks(context)

    assert report.safety_checks_passed is False
    assert "context is not fake-server-only" in report.blockers
