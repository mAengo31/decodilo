from lambda_m033_helpers import third_attempt_authorization

from decodilo.lambda_cloud.third_attempt_go_no_go import (
    build_lambda_third_attempt_go_no_go,
)


def test_complete_authorization_goes_for_future_m034_review_only():
    record = build_lambda_third_attempt_go_no_go(third_attempt_authorization())

    assert record.status == "go_for_future_m034_third_launch_review"
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_missing_authorization_needs_more_evidence():
    authorization = third_attempt_authorization(renewed_operator_approval_present=False)
    record = build_lambda_third_attempt_go_no_go(authorization)

    assert record.status == "needs_more_evidence"
    assert "renewed_operator_approval_missing" in record.blockers
