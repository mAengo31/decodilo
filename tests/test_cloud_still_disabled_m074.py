from decodilo.lambda_cloud.m074_report import LambdaM074Report
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    LambdaM075RRuntimeProtocolSmokeAuthorization,
)


def test_m074_future_artifacts_do_not_enable_cloud() -> None:
    auth = LambdaM075RRuntimeProtocolSmokeAuthorization(
        authorization_status="authorized_for_future_m075r_runtime_protocol_smoke",
    )

    assert auth.future_only is True
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False
    assert auth.billable_action_performed is False


def test_m074_report_keeps_launch_disabled() -> None:
    report = LambdaM074Report(
        report_passed=True,
        tiny_smoke_success_status="tiny_smoke_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        runtime_protocol_readiness_status="ready_for_future_runtime_protocol_smoke_planning",
        runtime_protocol_discovery_status="no_safe_runtime_protocol_smoke_command_found",
        runtime_protocol_policy_status="blocked_no_safe_command",
        m075r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_runtime_protocol_smoke_command",
        historical_billable_action_performed=True,
        m075r_blockers=["no_safe_runtime_protocol_smoke_command_found"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
