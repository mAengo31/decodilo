from lambda_m040_helpers import capacity_closeout

from decodilo.lambda_cloud.capacity_error_policy import (
    build_lambda_capacity_error_policy,
)


def test_capacity_policy_blocks_same_shape_retry_and_requires_availability_first():
    report = build_lambda_capacity_error_policy(closeout=capacity_closeout())

    assert report.no_immediate_automatic_retry is True
    assert report.same_shape_retry_blocked_without_fresh_availability is True
    assert report.availability_first_selector_required is True
    assert report.retry_strategy == "availability_first_required"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_operator_wait_and_retry_is_future_review_only():
    report = build_lambda_capacity_error_policy(
        closeout=capacity_closeout(),
        operator_accepts_wait_and_retry_for_future_review=True,
    )

    assert report.retry_strategy == "operator_wait_and_retry_for_future_review"
    assert report.operator_wait_and_retry_accepted_for_future_review is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
