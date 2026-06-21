from lambda_m035_helpers import attempt_history, endpoint_confidence, endpoint_verification

from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    build_lambda_launch_endpoint_confidence_review,
)


def test_medium_confidence_after_three_losses_requires_support(tmp_path):
    report = endpoint_confidence(tmp_path, "medium")

    assert report.endpoint_confidence_current == "medium"
    assert report.endpoint_confidence_recommended == "high"
    assert report.support_or_docs_confirmation_required is True
    assert "support_or_docs_confirmation_required_after_three_losses" in (
        report.confidence_blockers
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_high_confidence_can_pass_for_future_review(tmp_path):
    report = build_lambda_launch_endpoint_confidence_review(
        endpoint_verification=endpoint_verification("high"),
        attempt_history=attempt_history(tmp_path),
    )

    assert report.endpoint_confidence_current == "high"
    assert report.support_or_docs_confirmation_required is False
    assert report.confidence_blockers == []
