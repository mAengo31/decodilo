from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.pricing.registry import import_json_snapshot


def test_cloud_dry_run_still_has_no_launch_path_and_warns(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )

    report = LambdaDryRunPlanner().build_plan(
        run_id="no-launch",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=1,
        credits=7500,
        max_run_budget=1000,
    )

    assert report.plan.launch_allowed is False
    assert report.plan.teardown_plan is not None
    assert any("launch is disabled" in warning for warning in report.plan.warnings)
    assert any("availability" in warning for warning in report.plan.warnings)
