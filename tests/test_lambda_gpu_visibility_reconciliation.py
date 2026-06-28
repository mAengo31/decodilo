from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.gpu_visibility_reconciliation import (
    build_lambda_gpu_visibility_reconciliation_from_paths,
)


def test_gpu_visibility_reconciliation_passes_clean_m063(tmp_path):
    paths = write_m064_chain(tmp_path)

    report = build_lambda_gpu_visibility_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        final_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is True
    assert report.gpu_visibility_query_only_confirmed is True
    assert report.no_training_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_gpu_visibility_reconciliation_blocks_running_instance(tmp_path):
    paths = write_m064_chain(tmp_path, final_instance_count=1)

    report = build_lambda_gpu_visibility_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=paths["success"],
        final_discovery=paths["post_discovery"],
    )

    assert report.reconciliation_passed is False
    assert "final_discovery_visible_instances_present" in report.errors
