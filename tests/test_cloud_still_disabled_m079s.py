from __future__ import annotations

from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    LambdaM079R2NextSyntheticExperimentAuthorization,
)
from decodilo.lambda_cloud.m079s_report import LambdaM079SReport


def test_m079r2_authorization_remains_future_only_after_m079s() -> None:
    authorization = LambdaM079R2NextSyntheticExperimentAuthorization(
        authorization_status="authorized_for_future_m079r2_next_synthetic_experiment_retry",
        reason="retry_with_manifest_declared_artifact_capture_fixed",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m079s_report_keeps_launch_disabled() -> None:
    report = LambdaM079SReport(
        report_passed=True,
        m079r_closeout_status=(
            "closed_learner_syncer_smoke_command_passed_artifact_capture_blocked"
        ),
        command_passed=True,
        artifact_capture_blocked=True,
        declared_artifact_policy_fixed=True,
        parser_fixture_status="parsed_safe_learner_syncer_smoke_artifact",
        m079r2_authorization_status=(
            "authorized_for_future_m079r2_next_synthetic_experiment_retry"
        ),
        runbook_preview_status=(
            "ready_for_future_m079r2_next_synthetic_experiment_retry_review"
        ),
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
