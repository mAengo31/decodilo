from __future__ import annotations

from decodilo.lambda_cloud.m058_report import LambdaM058Report
from decodilo.lambda_cloud.m059_command_runbook_preview import (
    LambdaM059CommandRunbookPreview,
)
from decodilo.lambda_cloud.m059_remote_command_authorization import (
    LambdaM059RemoteCommandAuthorization,
)
from decodilo.lambda_cloud.preflight import run_lambda_preflight
from decodilo.lambda_cloud.remote_command_stage_policy import (
    build_lambda_remote_command_stage_policy,
)
from decodilo.lambda_cloud.smallest_useful_command_review import (
    LambdaSmallestUsefulCommandReview,
)


def test_m058_future_artifacts_keep_launch_and_billable_flags_false():
    policy = build_lambda_remote_command_stage_policy()
    review = LambdaSmallestUsefulCommandReview(
        review_status="review_passed",
        recommended_next_command_stage="identity_command",
        selected_future_command_set=["hostname"],
        command_risk="low",
    )
    auth = LambdaM059RemoteCommandAuthorization(
        authorization_status="authorized_for_future_m059_identity_command_review",
        selected_future_command_set=["hostname"],
    )
    preview = LambdaM059CommandRunbookPreview(
        preview_status="ready_for_future_m059_identity_command_review",
        selected_future_command_set=["hostname"],
    )

    for artifact in (policy, review, auth, preview):
        assert artifact.launch_ready is False
        assert artifact.launch_allowed is False
        assert artifact.billable_action_performed is False
        assert artifact.real_mutation_enabled is False


def test_m058_authorization_does_not_authorize_immediate_command():
    auth = LambdaM059RemoteCommandAuthorization(
        authorization_status="authorized_for_future_m059_identity_command_review",
        selected_future_command_set=["hostname"],
    )

    assert auth.launch_authorized_now is False
    assert auth.command_authorized_now is False
    assert auth.package_install_allowed is False
    assert auth.training_allowed is False


def test_m058_preflight_summary_keeps_launch_disabled():
    report = LambdaM058Report(
        success_record_status="ssh_noop_command_success",
        reconciliation_status="passed",
        closeout_status="closed_success",
        stage_policy_status="noop_command_only",
        selected_future_command_set=["hostname"],
        m059_authorization_status="authorized_for_future_m059_identity_command_review",
        runbook_preview_status="ready_for_future_m059_identity_command_review",
        report_passed=True,
        historical_billable_action_performed=True,
    )

    preflight = run_lambda_preflight(m058_report=report)

    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.m058_ssh_noop_closeout_summary is not None
    assert preflight.m058_ssh_noop_closeout_summary["report_passed"] is True
    assert preflight.m058_ssh_noop_closeout_summary["launch_ready"] is False
    assert preflight.m058_ssh_noop_closeout_summary["launch_allowed"] is False
