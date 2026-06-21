from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.fake_server_launch_terminate_flow import (
    run_fake_server_launch_terminate_flow,
)


def test_complete_fake_server_flow_passes():
    report = run_fake_server_launch_terminate_flow(context=fake_context())

    assert report.fake_launch_executed is True
    assert report.fake_terminate_executed is True
    assert report.duplicate_launch_safe is True
    assert report.duplicate_terminate_safe is True
    assert report.termination_verified is True
    assert report.real_lambda_api_used is False
    assert report.launch_allowed is False


def test_timeout_but_created_and_terminated_recover():
    report = run_fake_server_launch_terminate_flow(
        context=fake_context(),
        launch_failure_mode="launch_timeout_but_created",
        terminate_failure_mode="terminate_timeout_but_terminated",
    )

    assert report.termination_verified is True
    assert "launch_timeout_but_created" in report.recoverable_failures
    assert "terminate_timeout_but_terminated" in report.recoverable_failures
