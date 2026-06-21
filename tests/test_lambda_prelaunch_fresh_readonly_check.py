from decodilo.lambda_cloud.prelaunch_fresh_readonly_check import (
    LambdaPrelaunchFreshReadOnlyCheck,
)


def test_prelaunch_fresh_readonly_check_defaults_to_existing_evidence():
    report = LambdaPrelaunchFreshReadOnlyCheck()

    assert report.fresh_readonly_refresh_run is False
    assert report.source == "existing_m019c_evidence"
    assert report.mutating_operations == 0
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
