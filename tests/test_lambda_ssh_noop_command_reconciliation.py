from __future__ import annotations

from lambda_m058_helpers import write_m057_noop_workdir

from decodilo.lambda_cloud.ssh_noop_command_reconciliation import (
    build_lambda_ssh_noop_command_reconciliation_from_paths,
)
from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    build_lambda_ssh_noop_command_success_record_from_paths,
    write_lambda_ssh_noop_command_success_record,
)


def _success(paths):
    record = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )
    out = paths["workdir"].parent / "success.json"
    write_lambda_ssh_noop_command_success_record(out, record)
    return out


def test_noop_reconciliation_passes_clean_fixture(tmp_path):
    paths = write_m057_noop_workdir(tmp_path)

    report = build_lambda_ssh_noop_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=_success(paths),
        final_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is True
    assert report.command_scope_respected is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_noop_reconciliation_blocks_visible_instance(tmp_path):
    paths = write_m057_noop_workdir(tmp_path, final_instance_count=1)

    report = build_lambda_ssh_noop_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=_success(paths),
        final_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in report.errors
