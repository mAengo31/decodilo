from __future__ import annotations

from lambda_m058_helpers import write_m057_noop_workdir

from decodilo.lambda_cloud.ssh_noop_command_evidence_package import (
    build_lambda_ssh_noop_command_evidence_package_from_paths,
)
from decodilo.lambda_cloud.ssh_noop_command_reconciliation import (
    build_lambda_ssh_noop_command_reconciliation_from_paths,
    write_lambda_ssh_noop_command_reconciliation,
)
from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    build_lambda_ssh_noop_command_success_record_from_paths,
    write_lambda_ssh_noop_command_success_record,
)


def _inputs(tmp_path):
    paths = write_m057_noop_workdir(tmp_path)
    success = build_lambda_ssh_noop_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
        secret_scan=paths["secret_scan"],
    )
    success_path = tmp_path / "success.json"
    write_lambda_ssh_noop_command_success_record(success_path, success)
    reconcile = build_lambda_ssh_noop_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    reconcile_path = tmp_path / "reconcile.json"
    write_lambda_ssh_noop_command_reconciliation(reconcile_path, reconcile)
    return paths, success_path, reconcile_path


def test_noop_evidence_package_is_complete(tmp_path):
    paths, success, reconcile = _inputs(tmp_path)

    package = build_lambda_ssh_noop_command_evidence_package_from_paths(
        success_record=success,
        reconciliation=reconcile,
        secret_scan=paths["secret_scan"],
    )

    assert package.evidence_complete is True
    assert package.ssh_noop_command_success is True
    assert "run_report" in package.evidence_refs
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_noop_evidence_package_blocks_missing_journal(tmp_path):
    paths, success, reconcile = _inputs(tmp_path)
    (paths["workdir"] / "journal.jsonl").unlink()

    package = build_lambda_ssh_noop_command_evidence_package_from_paths(
        success_record=success,
        reconciliation=reconcile,
        secret_scan=paths["secret_scan"],
    )

    assert package.evidence_complete is False
    assert "journal" in package.missing_items
