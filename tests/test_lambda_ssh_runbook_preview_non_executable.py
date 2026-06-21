from __future__ import annotations

import pytest
from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m054_ssh_connectivity_runbook_preview import (
    LambdaM054SSHConnectivityRunbookPreview,
    build_lambda_m054_ssh_connectivity_runbook_preview_from_path,
)


def test_ssh_runbook_preview_ready_but_non_executable_for_approved_path(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m054_ssh_connectivity_runbook_preview_from_path(
        paths["authorization"],
    )

    assert report.preview_status == "ready_for_future_m054_ssh_connectivity_review"
    assert report.executable is False
    assert "remote command" in report.forbidden_actions
    assert "file transfer" in report.forbidden_actions
    assert "port forwarding" in report.forbidden_actions
    assert "package install" in report.forbidden_actions
    assert "training" in report.forbidden_actions
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_runbook_preview_blocks_declined_path(tmp_path):
    paths = write_m053_inputs(tmp_path, decline=True)

    report = build_lambda_m054_ssh_connectivity_runbook_preview_from_path(
        paths["authorization"],
    )

    assert report.preview_status == "blocked_not_authorized"
    assert report.executable is False


def test_ssh_runbook_preview_rejects_executable_preview():
    with pytest.raises(ValueError, match="must be non-executable"):
        LambdaM054SSHConnectivityRunbookPreview(
            preview_status="ready_for_future_m054_ssh_connectivity_review",
            authorization_status="authorized_for_future_m054_ssh_connectivity_review",
            executable=True,
        )
