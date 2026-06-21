from lambda_m035_helpers import price_snapshot

from decodilo.lambda_cloud.lower_cost_price_reconciliation import (
    reconcile_lambda_lower_cost_price,
)


def test_lower_cost_price_reconciles_under_budget():
    report = reconcile_lambda_lower_cost_price(price_snapshot=price_snapshot())

    assert report.price_reconciliation_passed is True
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.price_per_gpu_hour == 3.29
    assert report.price_per_instance_hour == 3.29
    assert report.base_estimated_cost == 1.645
    assert report.safety_buffer_adjusted_cost < 50
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_sample_price_snapshot_blocks_lower_cost_price_reconciliation():
    report = reconcile_lambda_lower_cost_price(price_snapshot=price_snapshot(sample=True))

    assert report.price_reconciliation_passed is False
    assert "sample_price_snapshot_cannot_support_future_lower_cost_review" in report.errors


def test_missing_price_blocks_lower_cost_price_reconciliation():
    report = reconcile_lambda_lower_cost_price(
        price_snapshot=price_snapshot(),
        shape="gpu_missing",
    )

    assert report.price_reconciliation_passed is False
    assert "selected_lower_cost_shape_missing_from_price_snapshot" in report.errors
