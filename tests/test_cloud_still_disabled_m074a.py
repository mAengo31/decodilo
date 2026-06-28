from decodilo.lambda_cloud.m074a_report import LambdaM074AReport
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    LambdaM075RRuntimeProtocolSmokeAuthorization,
)


def test_m074a_future_authorization_does_not_enable_cloud() -> None:
    authorization = LambdaM075RRuntimeProtocolSmokeAuthorization(
        authorization_status="authorized_for_future_m075r_runtime_protocol_smoke",
    )

    assert authorization.future_only is True
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m074a_report_keeps_launch_disabled() -> None:
    report = LambdaM074AReport(
        report_passed=True,
        runtime_smoke_command_added=True,
        discovery_status="found_safe_runtime_protocol_smoke_command",
        policy_status="policy_passed",
        m075r_authorization_status="authorized_for_future_m075r_runtime_protocol_smoke",
        runbook_preview_status="ready_for_future_m075r_runtime_protocol_smoke_review",
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
