from __future__ import annotations

from lambda_m047_helpers import write_m046c_workdir

from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths,
)


def test_clean_m046c_style_reconciliation_passes(tmp_path):
    paths = write_m046c_workdir(tmp_path)

    report = build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is True
    assert report.owned_instance_final_state == "terminated"
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_reconciliation_fails_when_running_instance_remains(tmp_path):
    paths = write_m046c_workdir(tmp_path, final_instance_count=1)

    report = build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in report.errors


def test_reconciliation_fails_when_unmanaged_instance_remains(tmp_path):
    paths = write_m046c_workdir(tmp_path, unmanaged_count=1)

    report = build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_unmanaged_instances_present" in report.errors
