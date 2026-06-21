from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)
from decodilo.lambda_cloud.minimal_mutation_preflight import (
    run_minimal_mutation_preflight,
)


def test_minimal_mutation_preflight_passes_fake_candidate():
    report = run_minimal_mutation_preflight(context=fake_context())

    assert report.preflight_passed is True
    assert report.fake_server_ready is True
    assert report.real_execution_allowed is False
    assert report.launch_allowed is False


def test_minimal_mutation_preflight_fails_missing_evidence():
    report = run_minimal_mutation_preflight(
        context=fake_context(),
        budget_lock_present=False,
    )

    assert report.preflight_passed is False
    assert "missing budget lock" in report.blockers


def test_minimal_mutation_preflight_fails_disabled_context():
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
    report = run_minimal_mutation_preflight(context=context)

    assert report.preflight_passed is False
    assert report.launch_ready is False
