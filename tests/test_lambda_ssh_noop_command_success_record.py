from __future__ import annotations

from lambda_m058_helpers import write_m057_noop_workdir

from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    build_lambda_ssh_noop_command_success_record_from_paths,
)


def test_m057_fixture_produces_ssh_noop_command_success(tmp_path):
    paths = write_m057_noop_workdir(tmp_path)

    record = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )

    assert record.status == "ssh_noop_command_success"
    assert record.command == "true"
    assert record.command_category == "noop"
    assert record.command_exit_code == 0
    assert record.historical_billable_action_performed is True
    assert record.billable_action_performed is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_noop_success_blocks_stdout_storage(tmp_path):
    paths = write_m057_noop_workdir(tmp_path, stdout_stored=True)

    record = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )

    assert record.status != "ssh_noop_command_success"
    assert "stdout_stored" in record.blockers


def test_noop_success_blocks_nonzero_command_exit(tmp_path):
    paths = write_m057_noop_workdir(tmp_path, command_exit_code=255)

    record = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )

    assert record.status != "ssh_noop_command_success"
    assert "command_exit_code_not_zero" in record.blockers
