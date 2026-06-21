from lambda_m037r_helpers import ssh_selection
from lambda_m040_helpers import candidates, rank

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    rank_lambda_availability_first_candidates,
)
from decodilo.lambda_cloud.live_capacity_candidate_extractor import (
    LambdaCapacityCandidate,
    LambdaLiveCapacityCandidateExtractorReport,
)


def test_cheapest_live_available_candidate_is_selected():
    report = rank(live=True)

    assert report.selection_status == "selected_live_available"
    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_1x_h100_pcie"
    assert report.launch_selection_allowed is True
    assert report.operator_risk_acceptance_required is False
    assert "live availability evidence" in report.selected_candidate_reason


def test_catalog_only_candidate_requires_risk_acceptance():
    report = rank(live=False)

    assert report.selection_status == "selected_catalog_only_requires_risk_acceptance"
    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_1x_h100_pcie"
    assert report.launch_selection_allowed is False
    assert report.operator_risk_acceptance_required is True
    assert any("catalog-only candidate is not launchable" in item for item in report.warnings)


def test_catalog_only_candidate_can_be_allowed_only_with_explicit_risk_acceptance():
    report = rank_lambda_availability_first_candidates(
        candidates=candidates(),
        ssh_key_selection=ssh_selection(),
        catalog_only_risk_accepted=True,
    )

    assert report.selection_status == "selected_catalog_only_risk_accepted"
    assert report.launch_selection_allowed is True
    assert report.catalog_only_risk_accepted is True


def test_missing_ssh_key_blocks_ranking():
    report = rank_lambda_availability_first_candidates(
        candidates=candidates(),
        ssh_key_selection=ssh_selection(ssh_key_names=()),
    )

    assert report.selection_status == "no_candidate"
    assert "no existing SSH key names discovered or selected" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_live_available_beats_lower_cost_catalog_candidate():
    extractor = LambdaLiveCapacityCandidateExtractorReport(
        live_candidates=[
            LambdaCapacityCandidate(
                shape="gpu_8x_a100_80gb_sxm4",
                gpu_type="A100 SXM 80GB",
                gpus_per_instance=8,
                region="us-west-1",
                price_per_instance_hour=22.32,
                estimated_30min_cost=11.16,
                buffered_estimated_30min_cost=12.834,
                source="live_instance_types",
                live_available=True,
            )
        ],
        product_catalog_candidates=[
            LambdaCapacityCandidate(
                shape="gpu_1x_h100_pcie",
                gpu_type="H100 PCIe",
                gpus_per_instance=1,
                region="us-west-1",
                price_per_instance_hour=3.29,
                estimated_30min_cost=1.645,
                buffered_estimated_30min_cost=1.89175,
                source="product_catalog",
                live_available=False,
            )
        ],
        availability_status="live_available",
    )
    report = rank_lambda_availability_first_candidates(
        candidates=extractor,
        ssh_key_selection=ssh_selection(),
    )

    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_8x_a100_80gb_sxm4"
    assert report.selection_status == "selected_live_available"


def test_lowest_buffered_cost_wins_within_live_candidates():
    extractor = LambdaLiveCapacityCandidateExtractorReport(
        live_candidates=[
            LambdaCapacityCandidate(
                shape="gpu_8x_a100_80gb_sxm4",
                gpu_type="A100 SXM 80GB",
                gpus_per_instance=8,
                region="us-west-1",
                price_per_instance_hour=22.32,
                estimated_30min_cost=11.16,
                buffered_estimated_30min_cost=12.834,
                source="live_instance_types",
                live_available=True,
            ),
            LambdaCapacityCandidate(
                shape="gpu_1x_h100_pcie",
                gpu_type="H100 PCIe",
                gpus_per_instance=1,
                region="us-west-1",
                price_per_instance_hour=3.29,
                estimated_30min_cost=1.645,
                buffered_estimated_30min_cost=1.89175,
                source="live_instance_types",
                live_available=True,
            ),
        ],
        product_catalog_candidates=[],
        availability_status="live_available",
    )
    report = rank_lambda_availability_first_candidates(
        candidates=extractor,
        ssh_key_selection=ssh_selection(),
    )

    assert report.selected_candidate is not None
    assert report.selected_candidate.shape == "gpu_1x_h100_pcie"


def test_no_auto_retry_and_owned_termination_are_required():
    report = rank_lambda_availability_first_candidates(
        candidates=candidates(live=True),
        ssh_key_selection=ssh_selection(),
        no_auto_launch_retry=False,
        owned_instance_termination_required=False,
    )

    assert report.selection_status == "no_candidate"
    assert "automatic_launch_retry_must_be_disabled" in report.blockers
    assert "owned_instance_termination_must_be_required" in report.blockers


def test_approved_shape_filter_is_respected():
    report = rank_lambda_availability_first_candidates(
        candidates=candidates(live=True),
        ssh_key_selection=ssh_selection(),
        approved_shapes={"gpu_8x_a100_80gb_sxm4"},
    )

    assert report.selection_status == "no_candidate"
    assert "no_viable_availability_first_candidate" in report.blockers
