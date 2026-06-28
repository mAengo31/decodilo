from __future__ import annotations

from decodilo.lambda_cloud.m088_report import LambdaM088Report
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    LambdaM089RBoundedDilocoExperimentAuthorization,
)


def test_m089r_future_authorization_cannot_enable_launch():
    authorization = LambdaM089RBoundedDilocoExperimentAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_bounded_diloco_experiment_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m088_report_cannot_enable_launch():
    report = LambdaM088Report(
        report_passed=True,
        parameter_fragment_success_status="remote_parameter_fragment_smoke_success",
        parameter_fragment_closeout_status="closed_with_warnings",
        parameter_fragment_closeout_succeeded=True,
        parameter_fragment_artifact_audit_passed=True,
        ssh_history_update_status="ssh_proven_candidate_history_updated",
        gpu_1x_a10_us_west_1_recorded=True,
        gpu_1x_a10_us_east_1_preserved=True,
        scaffold_status="scaffold_validation_complete",
        bounded_readiness_status=(
            "ready_for_first_bounded_synthetic_diloco_experiment_planning"
        ),
        bounded_discovery_status="no_safe_bounded_diloco_experiment_command_found",
        bounded_policy_status="blocked_no_safe_command",
        m089r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_bounded_diloco_experiment_command",
        historical_billable_action_performed=True,
        m089r_blockers=["m089r_not_authorized"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
