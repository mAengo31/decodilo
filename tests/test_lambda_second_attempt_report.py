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
from decodilo.lambda_cloud.second_attempt_report import build_lambda_second_attempt_report
from decodilo.lambda_cloud.second_attempt_risk_review import (
    build_lambda_second_attempt_risk_review,
)


def test_second_attempt_report_serializes_and_keeps_flags_false():
    incident = closed_m029_incident()
    risk = build_lambda_second_attempt_risk_review(incident)
    mitigation = build_lambda_response_loss_mitigation_review(
        incident=incident,
        prior_m029_report=prior_m029_report(),
    )
    correlation = build_lambda_second_attempt_correlation_plan(
        prior_m029_report=prior_m029_report(),
        m029_authorization=m029_authorization_package(),
    )
    reconciliation = build_lambda_second_attempt_reconciliation_plan()
    authorization = build_lambda_second_attempt_authorization(
        incident=incident,
        risk_review=risk,
        mitigation_review=mitigation,
        correlation_plan=correlation,
        reconciliation_plan=reconciliation,
    )
    go_no_go = build_lambda_second_attempt_go_no_go(authorization)

    report = build_lambda_second_attempt_report(
        risk_review=risk,
        mitigation_review=mitigation,
        correlation_plan=correlation,
        reconciliation_plan=reconciliation,
        authorization=authorization,
        go_no_go=go_no_go,
    )

    assert report.report_passed is True
    assert report.launch_allowed is False
    assert "future M031" in report.to_json()
