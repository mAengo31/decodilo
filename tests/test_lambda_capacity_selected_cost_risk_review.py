from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    build_lambda_capacity_selected_cost_risk_review_from_paths,
    load_lambda_capacity_selected_cost_risk_review,
)


def test_capacity_selected_cost_risk_review_passes_under_budget(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_capacity_selected_cost_risk_review(paths["cost_m045"])

    assert report.cost_risk_review_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.estimated_30min_cost == 11.16
    assert report.buffered_estimated_30min_cost == 12.834
    assert report.prior_excluded_candidate == "gpu_1x_h100_pcie"
    assert report.prior_exclusion_reason == "recent_capacity_error_excluded"
    assert report.candidate_larger_than_lifecycle_smoke_minimum is True
    assert report.catalog_backed_not_live_confirmed is True
    assert any("larger" in warning for warning in report.warnings)
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_selected_cost_risk_review_blocks_sample_price(tmp_path):
    paths = write_m045_inputs(tmp_path, sample_price=True)
    report = build_lambda_capacity_selected_cost_risk_review_from_paths(
        selector_output=paths["selector_m044h"],
        price_snapshot=paths["prices"],
        capacity_history=paths["history"],
        response_loss_controls=paths["controls"],
        ssh_key_selection=paths["ssh"],
    )

    assert report.cost_risk_review_passed is False
    assert "sample_price_snapshot_cannot_authorize_capacity_selected_review" in (
        report.blockers
    )


def test_capacity_selected_cost_risk_review_blocks_over_budget(tmp_path):
    paths = write_m045_inputs(tmp_path, over_budget=True)
    report = load_lambda_capacity_selected_cost_risk_review(paths["cost_m045"])

    assert report.cost_risk_review_passed is False
    assert "buffered_estimated_cost_not_below_max_budget" in report.blockers
