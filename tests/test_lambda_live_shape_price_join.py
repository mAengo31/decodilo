from __future__ import annotations

from lambda_m047_helpers import SUCCESS_SHAPE, write_price_snapshot_fixture

from decodilo.lambda_cloud.live_shape_price_join import (
    build_lambda_live_shape_price_join_from_paths,
)


def test_live_shape_price_join_matches_non_sample_price(tmp_path):
    price_snapshot = tmp_path / "prices.json"
    write_price_snapshot_fixture(price_snapshot)

    report = build_lambda_live_shape_price_join_from_paths(
        price_snapshot=price_snapshot,
        live_instance_type_name=SUCCESS_SHAPE,
    )

    assert report.join_status == "matched"
    assert report.estimated_30min_cost == 11.16
    assert report.buffered_estimated_30min_cost == 12.834
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_sample_price_snapshot_blocks_price_join(tmp_path):
    price_snapshot = tmp_path / "prices.json"
    write_price_snapshot_fixture(price_snapshot, sample=True)

    report = build_lambda_live_shape_price_join_from_paths(
        price_snapshot=price_snapshot,
        live_instance_type_name=SUCCESS_SHAPE,
    )

    assert "sample_price_snapshot_not_allowed" in report.blockers


def test_missing_price_blocks_price_join(tmp_path):
    price_snapshot = tmp_path / "prices.json"
    write_price_snapshot_fixture(price_snapshot)

    report = build_lambda_live_shape_price_join_from_paths(
        price_snapshot=price_snapshot,
        live_instance_type_name="gpu_missing",
    )

    assert report.join_status == "missing_price"
    assert "price_record_missing_for_live_shape" in report.blockers
