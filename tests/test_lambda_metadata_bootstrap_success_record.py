from __future__ import annotations

import pytest
from lambda_m052_helpers import write_m051b_workdir

from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    build_lambda_metadata_bootstrap_success_record_from_paths,
)


def test_m051b_fixture_produces_metadata_bootstrap_success(tmp_path):
    paths = write_m051b_workdir(tmp_path)

    record = build_lambda_metadata_bootstrap_success_record_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status == "metadata_bootstrap_success"
    assert record.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert record.selected_region == "us-midwest-1"
    assert record.historical_billable_action_performed is True
    assert record.billable_action_performed is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_success_record_rejects_ssh_attempt(tmp_path):
    paths = write_m051b_workdir(tmp_path, ssh_attempted=True)

    with pytest.raises(ValueError, match="remote execution"):
        build_lambda_metadata_bootstrap_success_record_from_paths(
            workdir=paths["workdir"],
            post_discovery=paths["post_discovery"],
        )


def test_success_record_blocks_missing_termination_verification(tmp_path):
    paths = write_m051b_workdir(tmp_path, termination_verified=False)

    record = build_lambda_metadata_bootstrap_success_record_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status == "metadata_bootstrap_partial"
    assert "termination_not_verified" in record.blockers


def test_success_record_blocks_final_visible_instance(tmp_path):
    paths = write_m051b_workdir(tmp_path, final_instance_count=1)

    record = build_lambda_metadata_bootstrap_success_record_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status != "metadata_bootstrap_success"
    assert "final_instance_count_nonzero" in record.blockers
