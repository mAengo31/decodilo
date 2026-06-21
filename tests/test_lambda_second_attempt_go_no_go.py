from lambda_m030_helpers import closed_m029_incident, m029_authorization_package, prior_m029_report

from decodilo.lambda_cloud.response_loss_mitigation_review import (
    build_lambda_response_loss_mitigation_review,
)
from decodilo.lambda_cloud.second_attempt_authorization import (
    build_lambda_second_attempt_authorization,
)
from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    build_lambda_second_attempt_correlation_plan,
)
from decodilo.lambda_cloud.second_attempt_go_no_go import (
    build_lambda_second_attempt_go_no_go,
)
from decodilo.lambda_cloud.second_attempt_reconciliation_plan import (
    build_lambda_second_attempt_reconciliation_plan,
)
from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
)


def test_complete_authorization_goes_for_future_m031_review_only():
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

    record = build_lambda_second_attempt_go_no_go(authorization)

    assert record.status == "go_for_future_m031_second_launch_review"
    assert record.launch_allowed is False
