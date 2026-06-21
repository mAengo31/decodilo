from decodilo.lambda_cloud.flexible_selector_operator_approval import (
    build_lambda_flexible_selector_operator_approval,
)


def test_flexible_selector_operator_approval_complete():
    report = build_lambda_flexible_selector_operator_approval(
        approve_future_review=True,
        acknowledge_all=True,
    )

    assert report.approval_status == "approved_for_future_flexible_selector_launch_review"
    assert report.approval_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_flexible_selector_operator_approval_incomplete_blocks():
    report = build_lambda_flexible_selector_operator_approval(
        approve_future_review=True,
        acknowledge_all=False,
    )

    assert report.approval_status == "not_provided"
    assert report.approval_complete is False
    assert any(item.startswith("missing_acknowledgement:") for item in report.blockers)


def test_flexible_selector_operator_decline_wait():
    report = build_lambda_flexible_selector_operator_approval(
        decline_wait_for_live_availability=True,
    )

    assert report.approval_status == "declined_wait_for_live_availability"
    assert report.approval_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
