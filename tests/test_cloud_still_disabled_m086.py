from __future__ import annotations

from decodilo.lambda_cloud.m086_report import LambdaM086Report
from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    LambdaM087RParameterFragmentAuthorization,
)


def test_m086_future_authorization_cannot_enable_launch():
    authorization = LambdaM087RParameterFragmentAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_parameter_fragment_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m086_report_cannot_enable_launch():
    report = LambdaM086Report(
        report_passed=True,
        integrated_success_status="remote_integrated_diloco_synthetic_success",
        integrated_closeout_status="closed_with_warnings",
        integrated_closeout_succeeded=True,
        integrated_artifact_audit_passed=True,
        ssh_history_update_status="ssh_proven_candidate_history_updated",
        gpu_1x_a10_us_west_1_recorded=True,
        gpu_1x_a10_us_east_1_preserved=True,
        parameter_fragment_readiness_status=(
            "ready_for_future_parameter_fragment_planning"
        ),
        parameter_fragment_discovery_status="no_safe_parameter_fragment_command_found",
        parameter_fragment_policy_status="blocked_no_safe_command",
        m087r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_parameter_fragment_command",
        historical_billable_action_performed=True,
        m087r_blockers=["no_safe_parameter_fragment_command_found"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
