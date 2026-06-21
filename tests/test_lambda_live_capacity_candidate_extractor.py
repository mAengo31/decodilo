from lambda_m035_helpers import price_snapshot
from lambda_m037r_helpers import discovery
from lambda_m040_helpers import candidates

from decodilo.lambda_cloud.live_capacity_candidate_extractor import (
    extract_lambda_capacity_candidates,
)


def test_live_candidates_extracted_from_fixture():
    report = candidates(live=True)

    assert report.availability_status == "live_available"
    assert report.live_candidates[0].shape == "gpu_1x_h100_pcie"
    assert report.product_catalog_candidates


def test_zero_instance_types_is_endpoint_inconclusive_with_catalog_candidates():
    report = candidates(live=False)

    assert report.availability_status == "endpoint_inconclusive"
    assert not report.live_candidates
    assert {item.shape for item in report.product_catalog_candidates} >= {
        "gpu_1x_h100_pcie",
        "gpu_8x_h100_sxm",
    }


def test_sample_price_snapshot_blocks_candidate_extraction():
    report = extract_lambda_capacity_candidates(
        discovery=discovery(),
        price_snapshot=price_snapshot(sample=True),
    )

    assert "sample_price_snapshot_cannot_rank_capacity_candidates" in report.errors
    assert report.launch_ready is False
    assert report.launch_allowed is False
