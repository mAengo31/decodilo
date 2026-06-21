from lambda_m030_helpers import (
    closed_m029_incident,
    m029_authorization_package,
    open_m029_incident,
    prior_m029_report,
)

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    build_lambda_response_loss_mitigation_review,
)
from decodilo.lambda_cloud.second_attempt_authorization import (
    build_lambda_second_attempt_authorization,
)
from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    build_lambda_second_attempt_correlation_plan,
)
from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    build_lambda_second_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
)


def test_closed_incident_and_passed_reviews_authorize_future_m031_only():
    incident = closed_m029_incident()
    authorization = build_lambda_second_attempt_authorization(
        incident=incident,
        risk_review=build_lambda_second_attempt_risk_review(incident),
        mitigation_review=build_lambda_response_loss_mitigation_review(
            incident=incident,
            prior_m029_report=prior_m029_report(),
        ),
        correlation_plan=build_lambda_second_attempt_correlation_plan(
            prior_m029_report=prior_m029_report(),
            m029_authorization=m029_authorization_package(),
        ),
        reconciliation_plan=build_lambda_second_attempt_reconciliation_plan(),
    )

    assert authorization.status == "authorized_for_future_m031_second_launch_attempt"
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_open_incident_not_authorized():
    incident = open_m029_incident()
    authorization = build_lambda_second_attempt_authorization(
        incident=incident,
        risk_review=build_lambda_second_attempt_risk_review(incident),
        mitigation_review=build_lambda_response_loss_mitigation_review(
            incident=incident,
            prior_m029_report=prior_m029_report(),
        ),
        correlation_plan=build_lambda_second_attempt_correlation_plan(
            prior_m029_report=prior_m029_report(),
            m029_authorization=m029_authorization_package(),
        ),
        reconciliation_plan=build_lambda_second_attempt_reconciliation_plan(),
    )

    assert authorization.status == "not_authorized"
    assert "m029c_incident_not_closed" in authorization.blockers
