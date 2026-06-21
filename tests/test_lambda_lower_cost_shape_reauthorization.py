from lambda_m035_helpers import price_snapshot
from lambda_m036_helpers import lower_cost_review, support_response

from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    build_lambda_lower_cost_shape_reauthorization,
)


def test_h100_pcie_1x_recommended_for_lifecycle_smoke():
    report = lower_cost_review()

    assert report.decision.status == "reauthorize_lower_cost_shape"
    assert report.recommended_candidate is not None
    assert report.recommended_candidate.shape == "gpu_1x_h100_pcie"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_no_candidate_keeps_current_shape():
    snapshot = price_snapshot()
    report = build_lambda_lower_cost_shape_reauthorization(
        price_snapshot=snapshot,
        current_shape="gpu_1x_h100_pcie",
    )

    assert report.decision.status == "keep_current_shape"


def test_support_unavailable_blocks_lower_cost_selection():
    report = build_lambda_lower_cost_shape_reauthorization(
        price_snapshot=price_snapshot(),
        current_shape="gpu_8x_h100_sxm",
        support_response=support_response(pcie_available=False),
    )

    assert report.decision.status == "keep_current_shape"
    assert report.recommended_candidate is None

