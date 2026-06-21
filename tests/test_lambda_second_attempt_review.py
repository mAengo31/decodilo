from lambda_m030_helpers import closed_m029_incident, prior_m029_report

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    build_lambda_response_loss_mitigation_review,
)
from decodilo.lambda_cloud.second_attempt_review import build_lambda_second_attempt_review
from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
)


def test_second_attempt_review_combines_risk_and_mitigation():
    incident = closed_m029_incident()
    report = build_lambda_second_attempt_review(
        risk_review=build_lambda_second_attempt_risk_review(incident),
        mitigation_review=build_lambda_response_loss_mitigation_review(
            incident=incident,
            prior_m029_report=prior_m029_report(),
        ),
    )

    assert report.review_passed is True
    assert report.launch_ready is False
