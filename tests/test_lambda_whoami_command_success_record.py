from __future__ import annotations

from lambda_m062_helpers import write_m061_whoami_workdir

from decodilo.lambda_cloud.whoami_command_success_record import (
    build_lambda_whoami_command_success_record_from_paths,
)


def test_whoami_success_record_passes_clean_m061_fixture(tmp_path):
    paths = write_m061_whoami_workdir(tmp_path)

    record = build_lambda_whoami_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status == "whoami_command_success"
    assert record.command == "whoami"
    assert record.stdout_redacted is True
    assert record.raw_stdout_reported is False
    assert record.termination_verified is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_whoami_success_record_blocks_raw_stdout(tmp_path):
    paths = write_m061_whoami_workdir(
        tmp_path,
        stdout_stored=True,
        stdout_redacted="ubuntu",
    )

    record = build_lambda_whoami_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )

    assert record.status != "whoami_command_success"
    assert "whoami_stdout_not_redacted" in record.blockers
    assert "raw_stdout_reported" in record.blockers
