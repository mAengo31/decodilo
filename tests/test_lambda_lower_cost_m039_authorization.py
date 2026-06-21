from lambda_m038_helpers import authorization


def test_lower_cost_m039_authorization_future_only_when_approval_complete():
    report = authorization(approval_complete=True)

    assert report.authorization_status == "authorized_for_future_m039_lower_cost_launch_attempt"
    assert report.launch_authorized_for_next_milestone is True
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_m039_authorization_blocks_incomplete_operator_approval():
    report = authorization(approval_complete=False)

    assert report.authorization_status == "not_authorized"
    assert report.launch_authorized_for_next_milestone is False
    assert "operator approval is not marked complete" in report.blockers
