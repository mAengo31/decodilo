from lambda_m033_helpers import (
    capture_lock,
    correlation_plan,
    endpoint_confirmation,
    reconciliation_plan,
    risk_review,
    timeout_policy,
)

from decodilo.lambda_cloud.third_attempt_review import build_lambda_third_attempt_review


def test_combined_third_attempt_review_passes_complete_evidence():
    review = build_lambda_third_attempt_review(
        endpoint_confirmation=endpoint_confirmation(),
        response_capture_lock=capture_lock(),
        timeout_policy=timeout_policy(),
        risk_review=risk_review(),
        correlation_plan=correlation_plan(),
        reconciliation_plan=reconciliation_plan(),
    )

    assert review.review_passed is True
    assert review.launch_ready is False
    assert review.launch_allowed is False
