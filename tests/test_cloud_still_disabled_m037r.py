from lambda_m037r_helpers import m037r_report


def test_m037r_report_cannot_enable_launch(tmp_path):
    report = m037r_report(tmp_path)

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
