from __future__ import annotations

from test_lambda_m059_remote_command_authorization import _authorization_inputs

from decodilo.lambda_cloud.m058_report import build_lambda_m058_report_from_paths
from decodilo.lambda_cloud.m059_command_runbook_preview import (
    build_lambda_m059_command_runbook_preview_from_path,
    write_lambda_m059_command_runbook_preview,
)
from decodilo.lambda_cloud.m059_remote_command_authorization import (
    build_lambda_m059_remote_command_authorization_from_paths,
    write_lambda_m059_remote_command_authorization,
)


def test_m058_report_passes_for_clean_noop_closeout(tmp_path):
    closeout, policy, review = _authorization_inputs(tmp_path)
    auth_path = tmp_path / "auth.json"
    auth = build_lambda_m059_remote_command_authorization_from_paths(
        ssh_noop_closeout=closeout,
        stage_policy=policy,
        command_review=review,
    )
    write_lambda_m059_remote_command_authorization(auth_path, auth)
    preview_path = tmp_path / "preview.json"
    preview = build_lambda_m059_command_runbook_preview_from_path(
        authorization=auth_path,
    )
    write_lambda_m059_command_runbook_preview(preview_path, preview)

    report = build_lambda_m058_report_from_paths(
        success_record=tmp_path / "success.json",
        reconciliation=tmp_path / "reconciliation.json",
        closeout=closeout,
        stage_policy=policy,
        command_review=review,
        authorization=auth_path,
        runbook_preview=preview_path,
    )

    assert report.report_passed is True
    assert report.success_record_status == "ssh_noop_command_success"
    assert report.stage_policy_status == "noop_command_only"
    assert report.selected_future_command_set == ["hostname"]
    assert (
        report.m059_authorization_status
        == "authorized_for_future_m059_identity_command_review"
    )
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
