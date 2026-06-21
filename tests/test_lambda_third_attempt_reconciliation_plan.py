from decodilo.lambda_cloud.third_attempt_reconciliation_plan import (
    build_lambda_third_attempt_reconciliation_plan,
)


def test_reconciliation_plan_contains_required_steps():
    plan = build_lambda_third_attempt_reconciliation_plan()

    assert plan.plan_passed is True
    assert plan.read_only_reconciliation_after_response_loss is True
    assert plan.final_read_only_termination_verification_required is True
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_low_confidence_candidate_is_not_terminable():
    plan = build_lambda_third_attempt_reconciliation_plan(candidate_confidence="low")

    assert plan.terminate_allowed_for_candidate is False


def test_exact_confidence_candidate_is_terminable_by_plan():
    plan = build_lambda_third_attempt_reconciliation_plan(candidate_confidence="exact")

    assert plan.terminate_allowed_for_candidate is True
