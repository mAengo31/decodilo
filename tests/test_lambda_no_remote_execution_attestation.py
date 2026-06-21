from __future__ import annotations

from lambda_m052_helpers import write_m051b_workdir

from decodilo.lambda_cloud.no_remote_execution_attestation import (
    build_lambda_no_remote_execution_attestation_from_paths,
)


def test_ssh_key_attached_without_ssh_passes(tmp_path):
    paths = write_m051b_workdir(tmp_path)

    report = build_lambda_no_remote_execution_attestation_from_paths(
        workdir=paths["workdir"],
    )

    assert report.ssh_key_attached_for_launch_payload is True
    assert report.attestation_passed is True
    assert report.ssh_attempted is False
    assert report.remote_command_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_attempt_blocks_attestation(tmp_path):
    paths = write_m051b_workdir(tmp_path, ssh_attempted=True)

    report = build_lambda_no_remote_execution_attestation_from_paths(
        workdir=paths["workdir"],
    )

    assert report.attestation_passed is False
    assert "ssh_attempted" in report.blockers


def test_remote_command_attempt_blocks_attestation(tmp_path):
    paths = write_m051b_workdir(tmp_path, remote_command_attempted=True)

    report = build_lambda_no_remote_execution_attestation_from_paths(
        workdir=paths["workdir"],
    )

    assert report.attestation_passed is False
    assert "remote_command_attempted" in report.blockers
