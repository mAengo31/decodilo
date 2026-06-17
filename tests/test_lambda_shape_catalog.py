import pytest

from decodilo.cloud.lambda_plan import LambdaDryRunPlanner
from decodilo.cloud.lambda_shapes import LambdaShape, LambdaShapeCatalog
from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.registry import import_json_snapshot


def test_shape_catalog_lookup_by_gpu_and_count() -> None:
    shape = LambdaShapeCatalog().lookup(gpu_type="H100 SXM", gpus_per_instance=8)

    assert shape.shape == "gpu_8x_h100_sxm"
    assert shape.gpu_memory_gb == 80


def test_ambiguous_shape_lookup_fails_closed() -> None:
    catalog = LambdaShapeCatalog(
        [
            LambdaShape(shape="shape-a", gpu_type="H100 SXM", gpus_per_instance=8),
            LambdaShape(shape="shape-b", gpu_type="H100 SXM", gpus_per_instance=8),
        ]
    )

    with pytest.raises(PricingAmbiguityError, match="ambiguous"):
        catalog.lookup(gpu_type="H100 SXM", gpus_per_instance=8)


def test_matching_price_without_matching_shape_cannot_plan(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    planner = LambdaDryRunPlanner(shape_catalog=LambdaShapeCatalog([]))

    with pytest.raises(PricingAmbiguityError, match="shape"):
        planner.build_plan(
            run_id="dry-run",
            price_snapshot_path=snapshot_path,
            gpu_type="H100 SXM",
            gpus_per_instance=8,
            nodes=1,
            hours=1,
            credits=7500,
            max_run_budget=1000,
        )
