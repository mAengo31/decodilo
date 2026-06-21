from __future__ import annotations

from lambda_m047_helpers import write_m046c_workdir

from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    build_lambda_lifecycle_smoke_success_record_from_paths,
)


def test_m046c_fixture_produces_lifecycle_smoke_success(tmp_path):
    paths = write_m046c_workdir(tmp_path)

    record = build_lambda_lifecycle_smoke_success_record_from_paths(
        workdir=paths["workdir"],
        final_summary=paths["final_summary"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status == "lifecycle_smoke_success"
    assert record.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert record.selected_region == "us-midwest-1"
    assert record.historical_billable_action_performed is True
    assert record.billable_action_performed is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_success_record_blocks_when_termination_is_not_verified(tmp_path):
    paths = write_m046c_workdir(tmp_path, termination_verified=False)

    record = build_lambda_lifecycle_smoke_success_record_from_paths(
        workdir=paths["workdir"],
        final_summary=paths["final_summary"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status == "lifecycle_smoke_partial"
    assert "termination_not_verified" in record.blockers


def test_success_record_blocks_when_final_instances_remain(tmp_path):
    paths = write_m046c_workdir(tmp_path, final_instance_count=1)

    record = build_lambda_lifecycle_smoke_success_record_from_paths(
        workdir=paths["workdir"],
        final_summary=paths["final_summary"],
        post_discovery=paths["post_discovery"],
    )

    assert record.status != "lifecycle_smoke_success"
    assert "final_instance_count_nonzero" in record.blockers
