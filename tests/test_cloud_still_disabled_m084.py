from __future__ import annotations

from decodilo.lambda_cloud.m084_report import LambdaM084Report
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    LambdaM085RIntegratedDilocoAuthorization,
)


def test_m085r_authorization_remains_future_only_after_m084() -> None:
    authorization = LambdaM085RIntegratedDilocoAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_integrated_diloco_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m084_report_keeps_launch_disabled() -> None:
    report = LambdaM084Report(
        report_passed=True,
        optimizer_success_status="remote_diloco_optimizer_smoke_success",
        optimizer_closeout_status="closed_with_warnings",
        optimizer_closeout_succeeded=True,
        optimizer_artifact_audit_passed=True,
        ssh_history_update_status="ssh_proven_candidate_history_updated",
        gpu_1x_a10_us_west_1_recorded=True,
        gpu_1x_a10_us_east_1_preserved=True,
        integrated_readiness_status="ready_for_future_integrated_diloco_planning",
        integrated_discovery_status="no_safe_integrated_diloco_command_found",
        integrated_policy_status="blocked_no_safe_command",
        m085r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_integrated_diloco_command",
        historical_billable_action_performed=True,
        m085r_blockers=["no_safe_integrated_diloco_command_found"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
