from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.catalog_rotation_cost_review import (
    build_lambda_catalog_rotation_cost_review_from_paths,
)


def test_catalog_rotation_cost_review_passes_under_budget(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_catalog_rotation_cost_review_from_paths(
        rotation_rank=paths["rotation"],
        price_snapshot=paths["prices"],
    )

    assert report.cost_review_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.estimated_30min_cost == 11.16
    assert report.buffered_estimated_30min_cost == 12.834
    assert report.incremental_cost_vs_prior_failed_candidate == 10.94225
    assert any("larger" in warning for warning in report.warnings)
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_cost_review_blocks_sample_price(tmp_path):
    paths = write_m044_inputs(tmp_path, sample_price=True)
    report = build_lambda_catalog_rotation_cost_review_from_paths(
        rotation_rank=paths["rotation"],
        price_snapshot=paths["prices"],
    )

    assert report.cost_review_passed is False
    assert "sample_price_snapshot_cannot_authorize_catalog_rotation" in report.blockers


def test_catalog_rotation_cost_review_blocks_over_budget(tmp_path):
    paths = write_m044_inputs(tmp_path, over_budget=True)
    report = build_lambda_catalog_rotation_cost_review_from_paths(
        rotation_rank=paths["rotation"],
        price_snapshot=paths["prices"],
    )

    assert report.cost_review_passed is False
    assert "buffered_estimated_cost_not_below_max_budget" in report.blockers
