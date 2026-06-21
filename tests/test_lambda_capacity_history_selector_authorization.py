from lambda_m044h_helpers import only_failed_shape_price_snapshot, write_m044h_inputs

from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)


def test_capacity_history_selector_authorization_passes_for_alternative(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_capacity_history_selector_authorization(
        paths["authorization_m044h"]
    )

    assert (
        report.authorization_status
        == "authorized_for_future_capacity_history_selector_review"
    )
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_history_selector_authorization_blocks_no_candidate(tmp_path):
    paths = write_m044h_inputs(tmp_path, prices=only_failed_shape_price_snapshot())
    report = load_lambda_capacity_history_selector_authorization(
        paths["authorization_m044h"]
    )

    assert report.authorization_status == "not_authorized"
    assert "capacity_history_selector_candidate_missing" in report.blockers
