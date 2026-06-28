from __future__ import annotations

from decodilo.lambda_cloud.first_experiment_readiness import (
    LambdaFirstExperimentReadiness,
)
from decodilo.lambda_cloud.m070_report import LambdaM070Report
from decodilo.lambda_cloud.m071r_first_experiment_authorization import (
    LambdaM071RFirstExperimentAuthorization,
)
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m070_future_artifacts_do_not_enable_cloud() -> None:
    readiness = LambdaFirstExperimentReadiness(
        readiness_status="ready_for_future_first_experiment_planning",
        cloud_lifecycle_ready=True,
        ssh_ready=True,
        source_upload_ready=True,
        dependency_bundle_ready=True,
        decodilo_cli_ready=True,
    )
    authorization = LambdaM071RFirstExperimentAuthorization(
        authorization_status="authorized_for_future_m071r_first_experiment_attempt",
    )

    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
    assert readiness.billable_action_performed is False
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m070_preflight_summary_keeps_launch_disabled() -> None:
    report = LambdaM070Report(
        report_passed=True,
        m069r_success_status="remote_decodilo_vslice_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        first_experiment_readiness_status="ready_for_future_first_experiment_planning",
        command_discovery_status="safe_experiment_command_found",
        m071r_authorization_status="authorized_for_future_m071r_first_experiment_attempt",
        runbook_preview_status="ready_for_future_m071r_first_experiment_review",
        historical_billable_action_performed=True,
    )

    preflight = run_lambda_preflight(m070_report=report)

    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.m070_remote_decodilo_vslice_summary is not None
    assert preflight.m070_remote_decodilo_vslice_summary["launch_ready"] is False
    assert preflight.m070_remote_decodilo_vslice_summary["launch_allowed"] is False
