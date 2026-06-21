from decodilo.lambda_cloud.lower_cost_operator_approval import (
    build_lambda_lower_cost_operator_approval_template,
)


def test_lower_cost_operator_approval_template_is_incomplete_by_default():
    report = build_lambda_lower_cost_operator_approval_template()

    assert report.approval_passed is False
    assert report.approval_complete_for_m039_review is False
    assert "operator approval is not marked complete" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_operator_approval_can_be_marked_complete_for_future_review():
    report = build_lambda_lower_cost_operator_approval_template(acknowledge_all=True)

    assert report.approval_passed is True
    assert report.approval_complete_for_m039_review is True
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False
