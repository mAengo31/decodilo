from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    build_lambda_second_attempt_reconciliation_plan,
)


def test_reconciliation_plan_contains_required_steps():
    plan = build_lambda_second_attempt_reconciliation_plan()

    assert plan.plan_passed is True
    assert plan.read_only_discovery_after_timeout is True
    assert plan.read_only_termination_verification_after_terminate is True
    assert plan.launch_ready is False


def test_terminate_disallowed_for_low_confidence_candidate():
    plan = build_lambda_second_attempt_reconciliation_plan(candidate_confidence="low")

    assert plan.terminate_allowed_for_candidate is False
    assert plan.terminate_disallowed_for_low_or_none_confidence is True


def test_exact_candidate_can_be_terminated_by_future_plan():
    plan = build_lambda_second_attempt_reconciliation_plan(candidate_confidence="exact")

    assert plan.terminate_allowed_for_candidate is True
    assert plan.launch_allowed is False
