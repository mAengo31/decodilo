from __future__ import annotations

from decodilo.lambda_cloud.m076_report import LambdaM076Report
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    LambdaM077RFirstSyntheticExperimentAuthorization,
)


def test_m077r_authorization_remains_future_only() -> None:
    authorization = LambdaM077RFirstSyntheticExperimentAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_first_synthetic_experiment_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m076_report_keeps_launch_disabled() -> None:
    report = LambdaM076Report(
        report_passed=True,
        runtime_smoke_success_status="runtime_protocol_smoke_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        first_synthetic_experiment_readiness_status=(
            "ready_for_future_first_synthetic_experiment_planning"
        ),
        first_synthetic_experiment_discovery_status=(
            "no_safe_first_synthetic_experiment_command_found"
        ),
        first_synthetic_experiment_policy_status="blocked_no_safe_command",
        m077r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_first_synthetic_experiment_command",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
