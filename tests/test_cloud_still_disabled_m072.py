from __future__ import annotations

from decodilo.lambda_cloud.m072_report import LambdaM072Report
from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    LambdaM073RTinySmokeAuthorization,
)
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m072_future_artifacts_do_not_enable_cloud() -> None:
    authorization = LambdaM073RTinySmokeAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_tiny_smoke_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m072_preflight_summary_keeps_launch_disabled() -> None:
    report = LambdaM072Report(
        report_passed=True,
        m071r_success_status="first_experiment_runtime_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        tiny_smoke_discovery_status="no_safe_tiny_smoke_command_found",
        tiny_smoke_policy_status="blocked_no_safe_command",
        m073r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_tiny_smoke_command",
        historical_billable_action_performed=True,
        m073r_blockers=["no_safe_tiny_smoke_command_found"],
    )

    preflight = run_lambda_preflight(m072_report=report)

    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.m072_first_experiment_closeout_summary is not None
    assert preflight.m072_first_experiment_closeout_summary["launch_ready"] is False
    assert preflight.m072_first_experiment_closeout_summary["launch_allowed"] is False
