from __future__ import annotations

from decodilo.lambda_cloud.m075r3_runtime_smoke_retry_authorization import (
    LambdaM075R3RuntimeSmokeRetryAuthorization,
)
from decodilo.lambda_cloud.m075t_report import LambdaM075TReport


def test_m075r3_authorization_remains_future_only() -> None:
    authorization = LambdaM075R3RuntimeSmokeRetryAuthorization(
        authorization_status="authorized_for_future_m075r3_runtime_smoke_retry",
        reason="retry_with_declared_artifact_body_or_summary_capture",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m075t_report_keeps_launch_disabled() -> None:
    report = LambdaM075TReport(
        report_passed=True,
        m075r2_closeout_status=(
            "closed_runtime_smoke_command_failed_with_artifact_metadata_captured"
        ),
        artifact_metadata_captured=True,
        body_or_summary_capture_required=True,
        artifact_body_policy_status="policy_defined",
        m075r3_authorization_status=(
            "authorized_for_future_m075r3_runtime_smoke_retry"
        ),
        runbook_preview_status="ready_for_future_m075r3_runtime_smoke_retry_review",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
