from __future__ import annotations

from lambda_m052_helpers import write_m052_inputs

from decodilo.lambda_cloud.remote_bootstrap_strategy_update import (
    build_lambda_remote_bootstrap_strategy_update_from_paths,
)


def test_successful_metadata_bootstrap_recommends_ssh_planning_only(tmp_path):
    paths = write_m052_inputs(tmp_path)

    report = build_lambda_remote_bootstrap_strategy_update_from_paths(
        metadata_closeout=paths["closeout"],
    )

    assert report.metadata_bootstrap_successful is True
    assert report.recommended_next_stage == "ssh_connectivity_planning"
    assert report.training_approved is False
    assert report.ssh_approved_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
