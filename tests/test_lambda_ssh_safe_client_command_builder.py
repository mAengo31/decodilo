from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    HOST_PLACEHOLDER,
    build_lambda_ssh_safe_client_command_from_path,
    validate_ssh_connectivity_command_preview,
)


def test_ssh_safe_client_command_preview_validates(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_safe_client_command_from_path(
        paths["private_key_policy"],
    )

    assert report.command_status == "safe_preview"
    assert report.executable is False
    assert report.handshake_only_guaranteed is True
    assert "-N" in report.command_preview
    assert "SessionType=none" in report.command_preview
    assert report.remote_command_present is False
    assert report.port_forwarding_detected is False
    assert report.launch_allowed is False


def test_ssh_safe_client_command_detects_remote_command():
    command = ["ssh", "-o", "SessionType=none", "-N", HOST_PLACEHOLDER, "nvidia-smi"]

    result = validate_ssh_connectivity_command_preview(command)

    assert "remote_command_present" in result["blockers"]
    assert result["remote_command_present"] is True


def test_ssh_safe_client_command_detects_forwarding_and_agent_options():
    command = ["ssh", "-L", "1:host:1", "-A", "-X", "-t", HOST_PLACEHOLDER]

    result = validate_ssh_connectivity_command_preview(command)

    assert "unsafe_ssh_option:-L" in result["blockers"]
    assert "unsafe_ssh_option:-A" in result["blockers"]
    assert "unsafe_ssh_option:-X" in result["blockers"]
    assert "unsafe_ssh_option:-t" in result["blockers"]
    assert result["port_forwarding_detected"] is True
