from __future__ import annotations

from decodilo.lambda_cloud.m080_report import LambdaM080Report
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
)


def test_m081r_authorization_remains_future_only_after_m080() -> None:
    authorization = LambdaM081RDilocoSyntheticAuthorization(
        authorization_status="not_authorized",
        blockers=["no_safe_diloco_synthetic_command_found"],
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m080_report_keeps_launch_disabled() -> None:
    report = LambdaM080Report(
        report_passed=True,
        learner_syncer_smoke_success_status="remote_learner_syncer_smoke_success",
        reconciliation_passed=True,
        closeout_status="closed_with_warnings",
        closeout_succeeded=True,
        artifact_audit_passed=True,
        diloco_synthetic_readiness_status="ready_for_future_diloco_synthetic_planning",
        diloco_synthetic_discovery_status="no_safe_diloco_synthetic_command_found",
        diloco_synthetic_policy_status="blocked_no_safe_command",
        m081r_authorization_status="not_authorized",
        runbook_preview_status="blocked_no_safe_diloco_synthetic_command",
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
