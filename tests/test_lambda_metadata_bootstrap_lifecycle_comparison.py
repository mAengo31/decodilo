from __future__ import annotations

from lambda_m052_helpers import write_m052_inputs

from decodilo.lambda_cloud.metadata_bootstrap_lifecycle_comparison import (
    build_lambda_metadata_bootstrap_lifecycle_comparison_from_paths,
)


def test_metadata_bootstrap_lifecycle_comparison_lists_remaining_work(tmp_path):
    paths = write_m052_inputs(tmp_path)

    report = build_lambda_metadata_bootstrap_lifecycle_comparison_from_paths(
        lifecycle_closeout=paths["lifecycle_closeout"],
        metadata_closeout=paths["closeout"],
        lifecycle_success_record=paths["lifecycle_success"],
        metadata_success_record=paths["success"],
    )

    assert report.lifecycle_smoke_success is True
    assert report.metadata_bootstrap_success is True
    assert "provider_metadata_collected" in report.added_capability
    assert "SSH" in report.still_not_done
    assert "training" in report.still_not_done
    assert report.launch_ready is False
    assert report.launch_allowed is False
