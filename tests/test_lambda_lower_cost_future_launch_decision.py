from lambda_m037r_helpers import authorization_package

from decodilo.lambda_cloud.lower_cost_future_launch_decision import (
    build_lambda_lower_cost_future_launch_decision,
)


def test_future_launch_decision_can_authorize_future_review_only(tmp_path):
    report = build_lambda_lower_cost_future_launch_decision(
        authorization_package=authorization_package(tmp_path)
    )

    assert report.decision_status == "authorized_for_future_lower_cost_launch_review"
    assert report.future_launch_review_authorized is True
    assert report.immediate_launch_authorized is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
