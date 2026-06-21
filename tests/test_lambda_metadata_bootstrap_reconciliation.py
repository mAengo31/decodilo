from __future__ import annotations

from lambda_m052_helpers import write_m051b_workdir

from decodilo.lambda_cloud.metadata_bootstrap_reconciliation import (
    build_lambda_metadata_bootstrap_reconciliation_from_paths,
)
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    build_lambda_metadata_bootstrap_success_record_from_paths,
    write_lambda_metadata_bootstrap_success_record,
)


def _write_success(paths):
    success_path = paths["workdir"].parent / "success.json"
    success = build_lambda_metadata_bootstrap_success_record_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_metadata_bootstrap_success_record(success_path, success)
    return success_path


def test_clean_metadata_bootstrap_reconciliation_passes(tmp_path):
    paths = write_m051b_workdir(tmp_path)
    success_path = _write_success(paths)

    report = build_lambda_metadata_bootstrap_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is True
    assert report.owned_instance_final_state == "terminated"
    assert report.metadata_only_confirmed is True
    assert report.no_ssh_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_reconciliation_fails_when_visible_instance_remains(tmp_path):
    paths = write_m051b_workdir(tmp_path, final_instance_count=1)
    success_path = _write_success(paths)

    report = build_lambda_metadata_bootstrap_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in report.errors


def test_reconciliation_fails_when_unmanaged_instance_remains(tmp_path):
    paths = write_m051b_workdir(tmp_path, unmanaged_count=1)
    success_path = _write_success(paths)

    report = build_lambda_metadata_bootstrap_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_unmanaged_instances_present" in report.errors
