from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_owned_instance_reconciliation import (
    reconcile_m029_owned_instance,
)


def test_exact_owned_id_allows_termination():
    report = reconcile_m029_owned_instance(
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        owned_instance_id="real-instance-1234567890",
    )

    assert report.confidence == "exact"
    assert report.terminate_allowed is True


def test_no_candidates_has_no_termination_target():
    report = reconcile_m029_owned_instance(
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        )
    )

    assert report.confidence == "none"
    assert report.terminate_allowed is False
    assert report.manual_review_required is False


def test_ambiguous_candidates_disallow_termination():
    report = reconcile_m029_owned_instance(
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=2,
            possible_owned_candidates=[
                {"instance_id": "fake-i-a", "instance_type": "gpu_8x_h100_sxm"},
                {"instance_id": "fake-i-b", "instance_type": "gpu_8x_h100_sxm"},
            ],
            confidence="possible_instance_created",
        ),
        planned_shape="gpu_8x_h100_sxm",
        planned_region="us-west-1",
    )

    assert report.terminate_allowed is False
    assert report.manual_review_required is True


def test_non_matching_candidate_disallows_termination():
    report = reconcile_m029_owned_instance(
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=1,
            possible_owned_candidates=[
                {"instance_id": "fake-i-a", "instance_type": "gpu_1x_h100_pcie"}
            ],
            confidence="possible_instance_created",
        ),
        planned_shape="gpu_8x_h100_sxm",
    )

    assert report.terminate_allowed is False
