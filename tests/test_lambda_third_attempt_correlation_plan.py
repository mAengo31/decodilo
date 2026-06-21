import pytest
from lambda_m030_helpers import m029_authorization_package
from lambda_m033_helpers import capture_lock, correlation_plan, timeout_policy

from decodilo.lambda_cloud.third_attempt_correlation_plan import (
    build_lambda_third_attempt_correlation_plan,
)


def test_valid_third_attempt_correlation_plan_uses_new_key():
    plan = correlation_plan()

    assert plan.plan_passed is True
    assert plan.idempotency_key not in plan.prior_idempotency_keys
    assert plan.no_automatic_retry is True
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_duplicate_prior_idempotency_key_fails_validation():
    plan = correlation_plan()

    with pytest.raises(ValueError, match="idempotency key must differ"):
        build_lambda_third_attempt_correlation_plan(
            m029_authorization=m029_authorization_package(),
            response_capture_lock=capture_lock(),
            timeout_policy=timeout_policy(),
            prior_idempotency_keys=[plan.idempotency_key],
        )


def test_missing_response_capture_lock_blocks_plan():
    bad_lock = capture_lock().model_copy(
        update={"lock_passed": False, "blockers": ["capture_http_status_before_parse"]}
    )
    plan = build_lambda_third_attempt_correlation_plan(
        m029_authorization=m029_authorization_package(),
        response_capture_lock=bad_lock,
        timeout_policy=timeout_policy(),
    )

    assert plan.plan_passed is False
    assert "response_capture_lock_failed" in plan.blockers
