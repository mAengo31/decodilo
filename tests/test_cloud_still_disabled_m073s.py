from __future__ import annotations

from decodilo.lambda_cloud.m073r2_retry_authorization import (
    LambdaM073R2RetryAuthorization,
)
from decodilo.lambda_cloud.m073s_report import LambdaM073SReport


def test_m073s_retry_authorization_does_not_enable_cloud() -> None:
    auth = LambdaM073R2RetryAuthorization(
        authorization_status="authorized_for_future_m073r2_tiny_smoke_retry",
    )

    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False
    assert auth.billable_action_performed is False


def test_m073s_report_keeps_launch_disabled() -> None:
    report = LambdaM073SReport(
        report_passed=True,
        classification="ssh_banner_exchange_timeout_during_upload",
        closeout_status="closed_source_upload_ssh_banner_timeout",
        banner_readiness_policy_status="policy_defined",
        upload_policy_status="policy_defined",
        m073r2_authorization_status="authorized_for_future_m073r2_tiny_smoke_retry",
        runbook_preview_status="ready_for_future_m073r2_tiny_smoke_retry_review",
        decodilo_not_tested=True,
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
