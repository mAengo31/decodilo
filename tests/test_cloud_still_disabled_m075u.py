from __future__ import annotations

from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    LambdaM075R4RuntimeSmokeRetryAuthorization,
)
from decodilo.lambda_cloud.m075u_report import LambdaM075UReport


def test_m075r4_authorization_remains_future_only() -> None:
    authorization = LambdaM075R4RuntimeSmokeRetryAuthorization(
        authorization_status="authorized_for_future_m075r4_runtime_smoke_retry",
        reason="local_update_stream_fix_verified",
        local_update_stream_fix_verified=True,
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m075u_report_keeps_launch_disabled() -> None:
    report = LambdaM075UReport(
        report_passed=True,
        m075r3_failure_status="runtime_smoke_update_stream_failed",
        m075r3_failed_check="protocol_or_event_check",
        m075r3_error_classification="update_stream_check_failed",
        m075r3_safe_error="update_stream_check_failed:TimeoutError",
        closeout_status="closed_runtime_smoke_update_stream_timeout",
        diagnostic_status="diagnosed_update_stream_timeout_path",
        local_reproduction_status="local_pass_remote_fail",
        local_before_runtime_smoke_status="passed",
        local_after_runtime_smoke_status="passed",
        runtime_smoke_now_passes_locally=True,
        code_fix_summary="local update-stream fix verified",
        m075r4_authorization_status=(
            "authorized_for_future_m075r4_runtime_smoke_retry"
        ),
        runbook_preview_status="ready_for_future_m075r4_runtime_smoke_retry_review",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
