from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)


def test_capacity_selected_m046_authorization_complete_future_only(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_capacity_selected_m046_authorization(
        paths["authorization_m046"]
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m046_capacity_selected_launch_review"
    )
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.launch_authorized_for_next_milestone is True
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_selected_m046_authorization_declined_not_authorized(tmp_path):
    paths = write_m045_inputs(tmp_path, approve=False, decline_wait=True)
    report = load_lambda_capacity_selected_m046_authorization(
        paths["authorization_m046"]
    )

    assert report.authorization_status == "not_authorized"
    assert "capacity_selected_operator_approval_not_approved" in report.blockers


def test_capacity_selected_m046_authorization_blocks_missing_cost_review(tmp_path):
    paths = write_m045_inputs(tmp_path, sample_price=True)
    report = load_lambda_capacity_selected_m046_authorization(
        paths["authorization_m046"]
    )

    assert report.authorization_status == "not_authorized"
    assert "capacity_selected_cost_risk_review_not_passed" in report.blockers
