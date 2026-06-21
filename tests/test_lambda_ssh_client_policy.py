from __future__ import annotations

from decodilo.lambda_cloud.ssh_client_policy import (
    build_lambda_ssh_client_policy,
    validate_future_openssh_options,
)


def test_ssh_client_policy_defaults_to_no_client():
    report = build_lambda_ssh_client_policy()

    assert report.allowed_client == "none"
    assert "openssh_batch_mode" in report.future_allowed_client_options
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_client_policy_rejects_unsafe_options_and_remote_command():
    blockers = validate_future_openssh_options(
        ["BatchMode=yes", "-tt", "-L", "8080:localhost:80"],
        remote_command="hostname",
    )

    assert "remote_command_present" in blockers
    assert "unsafe_ssh_option:-tt" in blockers
    assert "unsafe_ssh_option:-L" in blockers
