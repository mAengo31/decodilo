from __future__ import annotations

from decodilo.lambda_cloud.m082_report import LambdaM082Report
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    LambdaM083RDilocoOptimizerAuthorization,
)


def test_m083r_authorization_remains_future_only_after_m082() -> None:
    authorization = LambdaM083RDilocoOptimizerAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_diloco_optimizer_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m082_report_keeps_launch_disabled() -> None:
    report = LambdaM082Report(
        report_passed=True,
        diloco_synthetic_success_status="remote_diloco_shaped_synthetic_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        optimizer_readiness_status="ready_for_future_diloco_optimizer_planning",
        optimizer_discovery_status="no_safe_diloco_optimizer_command_found",
        optimizer_policy_status="blocked_no_safe_command",
        m083r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_diloco_optimizer_command",
        historical_billable_action_performed=True,
        m083r_blockers=["no_safe_diloco_optimizer_command_found"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
