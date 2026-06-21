from decodilo.lambda_cloud.lower_cost_launch_window_lock import (
    build_lambda_lower_cost_launch_window_lock,
)


def test_lower_cost_launch_window_lock_passes():
    report = build_lambda_lower_cost_launch_window_lock()

    assert report.launch_window_lock_passed is True
    assert report.max_runtime_minutes == 30
    assert report.max_launch_attempts == 1
    assert report.no_auto_launch_retry is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_launch_window_lock_blocks_auto_retry():
    report = build_lambda_lower_cost_launch_window_lock(no_auto_launch_retry=False)

    assert report.launch_window_lock_passed is False
    assert "automatic_launch_retry_forbidden" in report.blockers
