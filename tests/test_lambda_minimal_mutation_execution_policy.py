from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.minimal_mutation_execution_policy import (
    evaluate_minimal_mutation_execution_policy,
)


def test_complete_fake_evidence_allows_fake_execution_only():
    report = evaluate_minimal_mutation_execution_policy(
        context=fake_context(),
        m027_authorization_present=True,
        operation_spec_present=True,
        budget_lock_present=True,
        idempotency_plan_present=True,
        resource_scope_present=True,
        teardown_plan_present=True,
        termination_policy_present=True,
    )

    assert report.fake_execution_allowed is True
    assert report.real_execution_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_budget_or_idempotency_blocks():
    report = evaluate_minimal_mutation_execution_policy(
        context=fake_context(),
        m027_authorization_present=True,
        operation_spec_present=True,
        budget_lock_present=False,
        idempotency_plan_present=False,
        resource_scope_present=True,
        teardown_plan_present=True,
        termination_policy_present=True,
    )

    assert report.fake_execution_allowed is False
    assert "missing budget lock" in report.blockers
    assert "missing idempotency plan" in report.blockers


def test_unmanaged_billable_resource_blocks():
    report = evaluate_minimal_mutation_execution_policy(
        context=fake_context(),
        m027_authorization_present=True,
        operation_spec_present=True,
        budget_lock_present=True,
        idempotency_plan_present=True,
        resource_scope_present=True,
        teardown_plan_present=True,
        termination_policy_present=True,
        no_unmanaged_billable_resources=False,
    )

    assert report.fake_execution_allowed is False
    assert "unmanaged billable resources present" in report.blockers
