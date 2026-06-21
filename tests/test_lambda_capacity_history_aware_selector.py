from lambda_m044h_helpers import only_failed_shape_price_snapshot, write_m044h_inputs

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)


def test_capacity_history_selector_excludes_recent_failed_shape(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_capacity_history_aware_selector(paths["selector_m044h"])

    assert "gpu_1x_h100_pcie" in report.recent_capacity_failure_excluded_candidates
    assert report.exclusion_reasons["gpu_1x_h100_pcie"] == (
        "recent_capacity_error_excluded"
    )
    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_8x_a100_80gb_sxm4"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_history_selector_no_alternative_recommends_wait(tmp_path):
    paths = write_m044h_inputs(tmp_path, prices=only_failed_shape_price_snapshot())
    report = load_lambda_capacity_history_aware_selector(paths["selector_m044h"])

    assert report.selected_candidate is None
    assert report.selection_status == "no_candidate_wait_for_live_availability"
    assert report.recommended_next_step == "wait_for_live_availability"


def test_capacity_history_selector_fresh_live_availability_allows_failed_shape(tmp_path):
    paths = write_m044h_inputs(
        tmp_path,
        prices=only_failed_shape_price_snapshot(),
        live_failed_shape=True,
    )
    report = load_lambda_capacity_history_aware_selector(paths["selector_m044h"])

    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_1x_h100_pcie"
    assert report.selected_candidate.live_available is True
    assert report.recent_capacity_failure_excluded_candidates == []


def test_generic_catalog_risk_does_not_override_capacity_history(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_capacity_history_aware_selector(paths["selector_m044h"])

    assert report.same_shape_retry_acceptance_present is False
    assert "gpu_1x_h100_pcie" in report.recent_capacity_failure_excluded_candidates
