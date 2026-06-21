from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.ssh_connectivity_no_exec_audit import (
    build_lambda_ssh_connectivity_no_exec_audit_from_paths,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    LambdaSSHSafeClientCommandReport,
    write_lambda_ssh_safe_client_command,
)


def test_ssh_connectivity_no_exec_audit_passes_clean_preview(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_ssh_connectivity_no_exec_audit_from_paths(
        execution_plan=paths["execution_plan"],
        safe_client_command=paths["safe_command"],
    )

    assert report.audit_passed is True
    assert report.remote_exec_allowed is False
    assert report.interactive_shell_allowed is False
    assert report.command_string_present is False
    assert report.file_transfer_allowed is False
    assert report.port_forwarding_allowed is False
    assert report.package_install_allowed is False
    assert report.training_allowed is False


def test_ssh_connectivity_no_exec_audit_blocks_command_string(tmp_path):
    paths = write_m054a_inputs(tmp_path)
    unsafe = LambdaSSHSafeClientCommandReport(
        command_status="blocked",
        command_preview=["ssh", "lambda-user@<redacted-host>", "nvidia-smi"],
        command_preview_redacted="ssh lambda-user@<redacted-host> nvidia-smi",
        handshake_only_guaranteed=False,
        remote_command_present=True,
        blockers=["remote_command_present"],
    )
    write_lambda_ssh_safe_client_command(paths["safe_command"], unsafe)

    report = build_lambda_ssh_connectivity_no_exec_audit_from_paths(
        execution_plan=paths["execution_plan"],
        safe_client_command=paths["safe_command"],
    )

    assert report.audit_passed is False
    assert report.command_string_present is True
    assert "command_string_present" in report.blockers
