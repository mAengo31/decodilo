from lambda_m040_helpers import authorization

from decodilo.lambda_cloud.availability_first_authorization_package import (
    LambdaAvailabilityFirstAuthorizationPackage,
)
from decodilo.lambda_cloud.availability_first_go_no_go import (
    build_lambda_availability_first_go_no_go,
)


def test_complete_authorization_goes_for_future_review(tmp_path):
    report = build_lambda_availability_first_go_no_go(authorization(tmp_path))

    assert report.status == "go_for_future_availability_first_launch_review"
    assert report.future_review_allowed is True
    assert report.immediate_launch_authorized is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_same_shape_retry_without_availability_is_not_go():
    auth = LambdaAvailabilityFirstAuthorizationPackage(
        capacity_closeout_ref={"path": "closeout", "sha256": "a" * 64},
        rank_ref={"path": "rank", "sha256": "b" * 64},
        plan_ref={"path": "plan", "sha256": "c" * 64},
        authorization_status="not_authorized",
        operator_risk_acceptance_required=False,
        blockers=["availability_first_candidate_not_selected"],
    )

    report = build_lambda_availability_first_go_no_go(auth)

    assert report.status == "needs_more_evidence"
    assert report.future_review_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
