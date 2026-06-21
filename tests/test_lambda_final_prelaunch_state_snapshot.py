from lambda_m028_helpers import write_m028_core_artifacts

from decodilo.lambda_cloud.final_prelaunch_state_snapshot import (
    LambdaFinalPrelaunchStateSnapshot,
    build_lambda_final_prelaunch_state_snapshot,
)


def test_clean_snapshot_builds(tmp_path):
    paths = write_m028_core_artifacts(tmp_path)

    snapshot = build_lambda_final_prelaunch_state_snapshot(
        discovery_report=paths["valid_discovery"],
        m020_report=paths["m020"],
    )

    assert snapshot.snapshot_passed is True
    assert snapshot.launch_allowed is False


def test_unmanaged_billable_blocks_snapshot():
    snapshot = LambdaFinalPrelaunchStateSnapshot(
        source_discovery_ref="discovery",
        m020_report_ref="m020",
        required_endpoint_success=True,
        endpoint_count_succeeded=2,
        endpoint_count_unsupported_optional=0,
        unmanaged_count=1,
        unmanaged_billable_count=1,
        planned_instance_type="gpu_8x_h100_sxm",
        planned_region="us-west-1",
        planned_gpu_type="H100 SXM",
        planned_gpus_per_instance=8,
        selected_price_record_id="price",
        safety_buffer_adjusted_cost=10,
        snapshot_passed=False,
        blockers=["unmanaged billable resources present"],
    )

    assert snapshot.snapshot_passed is False
    assert snapshot.launch_ready is False
