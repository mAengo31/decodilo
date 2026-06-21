from lambda_m035_helpers import price_snapshot

from decodilo.lambda_cloud.launch_shape_strategy_review import (
    build_lambda_launch_shape_strategy_review,
)


def test_lower_cost_catalog_shape_recommended_for_lifecycle_smoke():
    report = build_lambda_launch_shape_strategy_review(
        price_snapshot=price_snapshot(),
        current_shape="gpu_8x_h100_sxm",
    )

    assert report.recommended_shape_strategy == "switch_to_lower_cost_shape"
    assert report.cheapest_safe_shape_if_available is not None
    assert report.cheapest_safe_shape_if_available["instance_type"] == "gpu_1x_h100_pcie"
    assert report.estimated_cost_current_30_min == 15.96
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_sample_snapshot_blocks_strategy():
    report = build_lambda_launch_shape_strategy_review(
        price_snapshot=price_snapshot(sample=True),
        current_shape="gpu_8x_h100_sxm",
    )

    assert report.recommended_shape_strategy == "unavailable"
    assert "sample_price_snapshot_cannot_support_shape_strategy" in report.blockers
