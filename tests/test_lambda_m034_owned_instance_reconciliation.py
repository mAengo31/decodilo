from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.m034_owned_instance_reconciliation import (
    reconcile_m034_owned_instance,
)


def test_exact_owned_id_allows_terminate():
    report = reconcile_m034_owned_instance(
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        owned_instance_id="fake-i-owned",
    )

    assert report.confidence == "exact"
    assert report.terminate_allowed is True


def test_no_candidates_no_terminate_needed():
    report = reconcile_m034_owned_instance(
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        )
    )

    assert report.confidence == "none"
    assert report.terminate_allowed is False
    assert report.manual_review_required is False


def test_ambiguous_candidate_disallows_termination():
    report = reconcile_m034_owned_instance(
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=2,
            possible_owned_candidates=[
                {"id": "fake-i-a", "status": "running"},
                {"id": "fake-i-b", "status": "running"},
            ],
            confidence="possible_instance_created",
        )
    )

    assert report.terminate_allowed is False
    assert report.manual_review_required is True
