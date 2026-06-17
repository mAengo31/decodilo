import pytest

from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.errors import BudgetExceededError, PricingAmbiguityError
from decodilo.pricing.registry import import_json_snapshot
from decodilo.pricing.snapshots import write_price_snapshot


def test_lambda_plan_rejects_over_budget(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )

    with pytest.raises(BudgetExceededError):
        LambdaDryRunPlanner().build_plan(
            run_id="dry-run",
            price_snapshot_path=snapshot_path,
            gpu_type="H100 SXM",
            gpus_per_instance=8,
            nodes=1,
            hours=10,
            credits=7500,
            max_run_budget=100,
        )


def test_lambda_plan_rejects_stale_snapshot_by_default(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    write_price_snapshot(
        snapshot_path,
        snapshot.model_copy(update={"captured_at_utc": "2026-01-01T00:00:00Z"}),
    )

    with pytest.raises(PricingAmbiguityError, match="stale"):
        LambdaDryRunPlanner().build_plan(
            run_id="dry-run",
            price_snapshot_path=snapshot_path,
            gpu_type="H100 SXM",
            gpus_per_instance=8,
            nodes=1,
            hours=1,
            credits=7500,
            max_run_budget=1000,
        )


def test_lambda_plan_with_scaling_fields_includes_capacity_plan(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )

    good = LambdaDryRunPlanner().build_plan(
        run_id="dry-run-good",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=2,
        credits=7500,
        max_run_budget=1000,
        params=1_000_000,
        bytes_per_param=2,
        expected_tokens_per_second=1000,
        expected_goodput=0.9,
        compression_bits=16,
    )
    poor = LambdaDryRunPlanner().build_plan(
        run_id="dry-run-poor",
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=2,
        credits=7500,
        max_run_budget=1000,
        params=1_000_000,
        bytes_per_param=2,
        expected_tokens_per_second=1000,
        expected_goodput=0.5,
        compression_bits=16,
    )

    assert good.plan.capacity_plan is not None
    assert poor.plan.capacity_plan is not None
    assert (
        poor.plan.capacity_plan["cost"]["expected_cost_per_useful_token"]
        > good.plan.capacity_plan["cost"]["expected_cost_per_useful_token"]
    )


def test_cloud_dry_run_compression_reduces_bandwidth_estimate(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    kwargs = dict(
        price_snapshot_path=snapshot_path,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        nodes=1,
        hours=2,
        credits=7500,
        max_run_budget=1000,
        params=1_000_000,
        bytes_per_param=4,
        expected_tokens_per_second=1000,
        expected_goodput=0.9,
    )
    uncompressed = LambdaDryRunPlanner().build_plan(run_id="dry-run-raw", **kwargs)
    compressed = LambdaDryRunPlanner().build_plan(
        run_id="dry-run-compressed",
        compression_bits=8,
        **kwargs,
    )

    assert compressed.plan.capacity_plan is not None
    assert uncompressed.plan.capacity_plan is not None
    assert (
        compressed.plan.capacity_plan["bandwidth"]["average_bandwidth_gbps"]
        < uncompressed.plan.capacity_plan["bandwidth"]["average_bandwidth_gbps"]
    )
