from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    LambdaM075R2RuntimeSmokeRetryAuthorization,
)
from decodilo.lambda_cloud.m075s_report import LambdaM075SReport


def test_m075r2_authorization_remains_future_only() -> None:
    authorization = LambdaM075R2RuntimeSmokeRetryAuthorization(
        authorization_status="authorized_for_future_m075r2_runtime_smoke_retry",
    )

    assert authorization.run_now is False
    assert authorization.future_only is True
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m075s_report_keeps_launch_disabled() -> None:
    report = LambdaM075SReport(
        report_passed=True,
        failure_status="runtime_smoke_command_failed",
        closeout_status="closed_runtime_smoke_command_failed_evidence_insufficient",
        failure_evidence_policy_status="policy_defined",
        artifact_policy_status="policy_defined",
        capture_policy_passed=True,
        m075r2_authorization_status="authorized_for_future_m075r2_runtime_smoke_retry",
        runbook_preview_status="ready_for_future_m075r2_runtime_smoke_retry_review",
        infrastructure_passed=True,
        failure_evidence_insufficient=True,
        historical_billable_action_performed=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
