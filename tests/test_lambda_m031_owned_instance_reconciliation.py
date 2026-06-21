from decodilo.lambda_cloud.m031_discovery_diff import LambdaM031DiscoveryDiffReport
from decodilo.lambda_cloud.m031_owned_instance_reconciliation import (
    reconcile_m031_owned_instance,
)


def test_exact_owned_id_allows_terminate():
    report = reconcile_m031_owned_instance(
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=1,
            confidence="possible_instance_created",
        ),
        owned_instance_id="real-instance-owned",
    )

    assert report.confidence == "exact"
    assert report.terminate_allowed is True


def test_no_candidates_means_no_terminate_needed():
    report = reconcile_m031_owned_instance(
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        )
    )

    assert report.confidence == "none"
    assert report.terminate_allowed is False
    assert report.manual_review_required is False


def test_ambiguous_candidates_disallow_terminate():
    report = reconcile_m031_owned_instance(
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=2,
            possible_owned_candidates=[
                {"instance_id": "fake-i-1", "status": "running"},
                {"instance_id": "fake-i-2", "status": "running"},
            ],
            confidence="possible_instance_created",
        )
    )

    assert report.terminate_allowed is False
    assert report.manual_review_required is True
