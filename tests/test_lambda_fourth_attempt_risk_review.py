from lambda_m035_helpers import attempt_history, endpoint_confidence

from decodilo.lambda_cloud.fourth_attempt_risk_review import (
    build_lambda_fourth_attempt_risk_review,
)


def test_fourth_attempt_risk_blocks_medium_endpoint_without_support(tmp_path):
    report = build_lambda_fourth_attempt_risk_review(
        attempt_history=attempt_history(tmp_path),
        endpoint_confidence=endpoint_confidence(tmp_path, "medium"),
    )

    assert report.prior_attempts_analyzed == 3
    assert report.prior_response_losses == 3
    assert report.fourth_attempt_risk_passed is False
    assert "endpoint_support_or_docs_confirmation_required" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_fourth_attempt_risk_passes_with_high_endpoint_confidence(tmp_path):
    report = build_lambda_fourth_attempt_risk_review(
        attempt_history=attempt_history(tmp_path),
        endpoint_confidence=endpoint_confidence(tmp_path, "high"),
    )

    assert report.fourth_attempt_risk_passed is True
    assert report.blockers == []
