from __future__ import annotations

from decodilo.lambda_cloud.m081r2_diloco_synthetic_authorization import (
    LambdaM081R2DilocoSyntheticAuthorization,
)
from decodilo.lambda_cloud.m081s_report import LambdaM081SReport


def test_m081r2_authorization_remains_future_only_after_m081s() -> None:
    authorization = LambdaM081R2DilocoSyntheticAuthorization(
        authorization_status="authorized_for_future_m081r2_diloco_synthetic_retry",
        reason="retry_with_manifest_declared_diloco_artifact_capture_fixed",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m081s_report_keeps_launch_disabled() -> None:
    report = LambdaM081SReport(
        report_passed=True,
        m081r_closeout_status="closed_diloco_smoke_command_passed_artifact_capture_blocked",
        command_passed=True,
        artifact_capture_blocked=True,
        manifest_declared_artifact_policy_fixed=True,
        parser_fixture_status="parsed_safe_diloco_smoke_artifact",
        m081r2_authorization_status="authorized_for_future_m081r2_diloco_synthetic_retry",
        runbook_preview_status="ready_for_future_m081r2_diloco_synthetic_retry_review",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
