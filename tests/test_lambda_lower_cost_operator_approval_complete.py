from decodilo.lambda_cloud.lower_cost_operator_approval import (
    build_lambda_lower_cost_operator_approval_template,
)


def test_lower_cost_operator_approval_complete_is_future_only():
    report = build_lambda_lower_cost_operator_approval_template(
        acknowledge_all=True,
        approve_future_m039=True,
    )

    assert report.approval_status == "approved_for_future_m039_lower_cost_launch_attempt"
    assert report.approval_passed is True
    assert report.approval_complete_for_m039_review is True
    assert report.ack_region_us_west_1 is True
    assert report.ack_no_ssh is True
    assert report.ack_no_ssh_key_create_delete is True
    assert report.ack_no_filesystem_create_delete is True
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False


def test_lower_cost_operator_approval_requires_explicit_future_approval():
    report = build_lambda_lower_cost_operator_approval_template(
        acknowledge_all=True,
        approve_future_m039=False,
    )

    assert report.approval_passed is False
    assert report.approval_complete_for_m039_review is False
    assert "future M039 lower-cost approval is not explicitly granted" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
