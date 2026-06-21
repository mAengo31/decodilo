from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.alternative_shape_operator_selection import (
    build_lambda_alternative_shape_operator_selection_from_paths,
)


def test_wait_option_valid(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_alternative_shape_operator_selection_from_paths(
        rotation_rank=paths["rotation"],
        wait_for_live_availability=True,
    )

    assert report.selection_status == "wait_selected"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_candidate_option_valid(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_alternative_shape_operator_selection_from_paths(
        rotation_rank=paths["rotation"],
        choose_catalog_candidate=True,
    )

    assert report.selection_status == "catalog_candidate_selected_for_future_review"
    assert report.selected_shape is not None
    assert report.operator_risk_acceptance_required is True


def test_manual_unknown_shape_blocks(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_alternative_shape_operator_selection_from_paths(
        rotation_rank=paths["rotation"],
        manual_shape="gpu_unknown",
        price_snapshot=paths["prices"],
    )

    assert report.selection_status == "selection_incomplete"
    assert "manual_shape_missing_non_sample_catalog_price" in report.blockers
