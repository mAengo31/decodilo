from lambda_m038_helpers import gate_check


def test_lower_cost_gate_check_passes_when_future_authorization_complete():
    report = gate_check(approval_complete=True)

    assert report.gate_passed is True
    assert report.effective_launch_timeout_seconds == 30.0
    assert report.response_capture_active is True
    assert report.status_before_parse is True
    assert report.no_auto_launch_retry is True
    assert report.strand_payload_compatible is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_gate_check_blocks_incomplete_operator_approval():
    report = gate_check(approval_complete=False)

    assert report.gate_passed is False
    assert "operator approval is not marked complete" in report.blockers
