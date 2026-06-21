from decodilo.lambda_cloud.capacity_history_selector_policy import (
    build_lambda_capacity_history_selector_policy,
)


def test_capacity_history_selector_policy_defaults_are_conservative():
    report = build_lambda_capacity_history_selector_policy()

    assert report.exclude_recent_capacity_failures is True
    assert report.require_fresh_live_availability_for_same_shape_retry is True
    assert report.allow_same_shape_retry_with_explicit_acceptance is False
    assert report.max_budget == 50
    assert report.quantity == 1
    assert report.no_auto_retry is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_history_selector_policy_can_record_explicit_retry_review_mode():
    report = build_lambda_capacity_history_selector_policy(
        allow_same_shape_retry_with_explicit_acceptance=True
    )

    assert report.allow_same_shape_retry_with_explicit_acceptance is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
