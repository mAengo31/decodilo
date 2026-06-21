from lambda_m030_helpers import closed_m029_incident, open_m029_incident

from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
)


def test_closed_incident_with_mitigation_review_passes_with_warnings():
    report = build_lambda_second_attempt_risk_review(closed_m029_incident())

    assert report.risk_review_passed is True
    assert report.incident_closed is True
    assert any(risk.name == "prior launch response lost" for risk in report.risks)
    assert report.launch_allowed is False


def test_open_incident_blocks_second_attempt_risk_review():
    report = build_lambda_second_attempt_risk_review(open_m029_incident())

    assert report.risk_review_passed is False
    assert "m029c_incident_not_closed" in report.blockers


def test_missing_mitigation_blocks_risk_review():
    report = build_lambda_second_attempt_risk_review(
        closed_m029_incident(),
        mitigation_review_present=False,
    )

    assert report.risk_review_passed is False
    assert "response_loss_mitigation_review_missing" in report.blockers
