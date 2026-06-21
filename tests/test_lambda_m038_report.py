from lambda_m038_helpers import m038_report


def test_m038_report_future_only_with_complete_approval_fixture():
    report = m038_report(approval_complete=True)

    assert report.authorization_status == "authorized_for_future_m039_lower_cost_launch_attempt"
    assert report.gate_passed is True
    assert report.command_preview_status == "ready_for_future_m039"
    assert report.report_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m038_report_records_incomplete_operator_approval_blocker():
    report = m038_report(approval_complete=False)

    assert report.authorization_status == "not_authorized"
    assert report.gate_passed is False
    assert "operator approval is not marked complete" in report.blockers
