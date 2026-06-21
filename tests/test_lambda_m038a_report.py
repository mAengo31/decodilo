from lambda_m038_helpers import m038a_report


def test_m038a_report_passes_for_future_candidate_only():
    report = m038a_report(approval_complete=True)

    assert (
        report.operator_approval_status
        == "approved_for_future_m039_lower_cost_launch_attempt"
    )
    assert (
        report.m039_authorization_status
        == "authorized_for_future_m039_lower_cost_launch_attempt"
    )
    assert report.gate_check_status == "passed"
    assert report.command_preview_status == "ready_for_future_m039"
    assert report.future_launch_candidate is True
    assert report.report_passed is True
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.estimated_30min_cost == 1.645
    assert report.buffered_estimated_30min_cost == 1.89175
    assert report.selected_ssh_key_hash is not None
    assert report.selected_ssh_key_hash.startswith("sha256:")
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_m038a_report_blocks_incomplete_operator_approval():
    report = m038a_report(approval_complete=False)

    assert report.future_launch_candidate is False
    assert report.report_passed is False
    assert report.gate_check_status == "blocked"
    assert "operator approval is not marked complete" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
