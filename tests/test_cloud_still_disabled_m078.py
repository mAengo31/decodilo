from __future__ import annotations

from decodilo.lambda_cloud.m078_report import LambdaM078Report
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    LambdaM079RNextSyntheticExperimentAuthorization,
)


def test_m079r_authorization_remains_future_only_after_m078() -> None:
    authorization = LambdaM079RNextSyntheticExperimentAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_next_synthetic_experiment_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m078_report_keeps_launch_disabled() -> None:
    report = LambdaM078Report(
        report_passed=True,
        synthetic_experiment_success_status="first_remote_synthetic_experiment_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        next_synthetic_experiment_readiness_status=(
            "ready_for_future_next_synthetic_experiment_planning"
        ),
        next_synthetic_experiment_discovery_status=(
            "no_safe_next_synthetic_experiment_command_found"
        ),
        next_synthetic_experiment_policy_status="blocked_no_safe_command",
        m079r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_next_synthetic_experiment_command",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
