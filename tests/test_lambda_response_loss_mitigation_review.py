from lambda_m030_helpers import closed_m029_incident, open_m029_incident, prior_m029_report

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    build_lambda_response_loss_mitigation_review,
)


def test_all_response_loss_mitigations_present_passes():
    report = build_lambda_response_loss_mitigation_review(
        incident=closed_m029_incident(),
        prior_m029_report=prior_m029_report(),
    )

    assert report.mitigation_passed is True
    assert report.automatic_retry_forbidden is True
    assert report.launch_ready is False


def test_same_idempotency_key_as_m029c_fails():
    report = build_lambda_response_loss_mitigation_review(
        incident=closed_m029_incident(),
        prior_m029_report=prior_m029_report(),
        second_idempotency_key="m029-launch-one-instance",
    )

    assert report.mitigation_passed is False
    assert "second_idempotency_key_distinct" in report.missing_mitigations


def test_missing_no_auto_retry_mitigation_fails():
    report = build_lambda_response_loss_mitigation_review(
        incident=closed_m029_incident(),
        prior_m029_report=prior_m029_report(),
        no_auto_retry=False,
    )

    assert report.mitigation_passed is False
    assert "automatic_retry_forbidden" in report.missing_mitigations


def test_open_incident_fails_mitigation_review():
    report = build_lambda_response_loss_mitigation_review(
        incident=open_m029_incident(),
        prior_m029_report=prior_m029_report(),
    )

    assert report.mitigation_passed is False
    assert "m029c_incident_closed" in report.missing_mitigations
