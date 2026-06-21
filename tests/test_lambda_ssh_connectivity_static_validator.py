from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    build_lambda_ssh_connectivity_static_validation_from_paths,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    LambdaSSHSafeClientCommandReport,
    write_lambda_ssh_safe_client_command,
)


def test_ssh_connectivity_static_validator_passes_clean_package(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_static_validation_from_paths(
        execution_plan=paths["execution_plan"],
        private_key_policy=paths["private_key_policy"],
        safe_client_command=paths["safe_command"],
    )

    assert report.static_validation_passed is True
    assert report.remote_exec_detected is False
    assert report.file_transfer_detected is False
    assert report.port_forwarding_detected is False
    assert report.unsafe_ssh_option_detected is False
    assert report.launch_allowed is False


def test_ssh_connectivity_static_validator_blocks_remote_command(tmp_path):
    paths = write_m054a_inputs(tmp_path)
    unsafe = LambdaSSHSafeClientCommandReport(
        command_status="blocked",
        command_preview=["ssh", "lambda-user@<redacted-host>", "python"],
        command_preview_redacted="ssh lambda-user@<redacted-host> python",
        handshake_only_guaranteed=False,
        remote_command_present=True,
        blockers=["remote_command_present"],
    )
    write_lambda_ssh_safe_client_command(paths["safe_command"], unsafe)

    report = build_lambda_ssh_connectivity_static_validation_from_paths(
        execution_plan=paths["execution_plan"],
        private_key_policy=paths["private_key_policy"],
        safe_client_command=paths["safe_command"],
    )

    assert report.static_validation_passed is False
    assert report.remote_exec_detected is True
    assert "remote_exec_detected" in report.blockers
