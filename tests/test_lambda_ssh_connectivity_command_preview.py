from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_command_preview import (
    build_lambda_ssh_connectivity_command_preview_from_paths,
)


def test_ssh_connectivity_command_preview_is_ready_but_non_executable(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_command_preview_from_paths(
        reviewer_bridge=paths["reviewer_bridge"],
        no_exec_audit=paths["no_exec_audit"],
    )

    assert report.preview_status == "ready_for_future_m054b_ssh_connectivity_review"
    assert report.executable is False
    assert "--m054-ssh-one-shot-arming" in report.command_preview
    assert "--m054-ssh-reviewer-bridge" in report.command_preview
    assert "--m054-ssh-static-validation" in report.command_preview
    assert "--m054-ssh-no-exec-audit" in report.command_preview
    assert "--m054-ssh-command-preview" in report.command_preview
    assert "remote command" in report.forbidden_actions
    assert "file transfer" in report.forbidden_actions
    assert "port forwarding" in report.forbidden_actions
    assert report.launch_allowed is False
