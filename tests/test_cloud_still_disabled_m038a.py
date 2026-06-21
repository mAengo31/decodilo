from lambda_m038_helpers import m038a_report


def test_m038a_report_keeps_cloud_execution_disabled():
    report = m038a_report(approval_complete=True)

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
