from lambda_m036_helpers import lower_cost_review, support_response

from decodilo.lambda_cloud.lower_cost_shape_operator_selection import (
    build_lambda_lower_cost_shape_operator_selection,
)


def test_support_confirms_1x_h100_pcie_selects_lower_cost_shape():
    report = build_lambda_lower_cost_shape_operator_selection(
        lower_cost_review=lower_cost_review(),
        support_response=support_response(),
    )

    assert report.selection_status == "select_lower_cost_shape"
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_support_says_unavailable_blocks_selection():
    report = build_lambda_lower_cost_shape_operator_selection(
        lower_cost_review=lower_cost_review(pcie_available=False),
        support_response=support_response(pcie_available=False),
    )

    assert report.selection_status == "lower_cost_shape_not_supported"


def test_no_support_answer_needs_operator_selection():
    report = build_lambda_lower_cost_shape_operator_selection(
        lower_cost_review=lower_cost_review(),
    )

    assert report.selection_status == "needs_operator_selection"

