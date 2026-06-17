import pytest

from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.no_op_client import NoOpCloudClient
from decodilo.pricing.registry import import_json_snapshot


def test_no_op_client_cannot_launch_and_counts_attempts() -> None:
    client = NoOpCloudClient()
    with pytest.raises(RuntimeError, match="cannot launch"):
        client.launch()
    assert client.api_calls_attempted == 1


def test_dry_run_planner_does_not_use_cloud_client(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    client = NoOpCloudClient()
    report = LambdaDryRunPlanner().build_plan(
        run_id="dry-run",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
    )

    assert report.plan.launch_allowed is False
    assert client.api_calls_attempted == 0
