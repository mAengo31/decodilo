from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m054_ssh_connectivity_runbook_preview import (
    build_lambda_m054_ssh_connectivity_runbook_preview_from_path,
)


def test_m054_runbook_preview_non_executable_and_blocked_without_authorization(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=False)

    report = build_lambda_m054_ssh_connectivity_runbook_preview_from_path(
        paths["authorization"],
    )

    assert report.preview_status == "blocked_not_authorized"
    assert report.executable is False
    assert "remote command" in report.forbidden_actions
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m054_runbook_preview_ready_for_future_review_when_authorized(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m054_ssh_connectivity_runbook_preview_from_path(
        paths["authorization"],
    )

    assert report.preview_status == "ready_for_future_m054_ssh_connectivity_review"
    assert report.executable is False
