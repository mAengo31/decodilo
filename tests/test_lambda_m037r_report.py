from lambda_m037r_helpers import m037r_report


def test_m037r_report_keeps_launch_disabled(tmp_path):
    report = m037r_report(tmp_path)

    assert report.future_launch_decision == "authorized_for_future_lower_cost_launch_review"
    assert report.lower_cost_shape == "gpu_1x_h100_pcie"
    assert report.strand_payload_compatible is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
