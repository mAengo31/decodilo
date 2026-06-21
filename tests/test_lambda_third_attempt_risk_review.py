from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m031d_helpers import closed_m031_closeout
from lambda_m033_helpers import (
    endpoint_confirmation,
    mitigation_acceptance,
    risk_review,
    timeout_policy,
)

from decodilo.lambda_cloud.third_attempt_risk_review import (
    build_lambda_third_attempt_risk_review,
)


def test_closed_incidents_and_accepted_mitigation_pass_risk_review():
    report = risk_review()

    assert report.third_attempt_risk_passed is True
    assert report.prior_response_losses == 2
    assert report.both_incidents_closed is True
    assert report.launch_allowed is False


def test_open_prior_incident_blocks_risk_review():
    report = build_lambda_third_attempt_risk_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m031d_closeout=closed_m031_closeout().model_copy(
            update={"closeout_succeeded": False}
        ),
        mitigation_acceptance=mitigation_acceptance(),
        endpoint_confirmation=endpoint_confirmation(),
        timeout_policy=timeout_policy(),
    )

    assert report.third_attempt_risk_passed is False
    assert "prior_incident_not_closed" in report.blockers


def test_missing_endpoint_confirmation_blocks_risk_review():
    report = build_lambda_third_attempt_risk_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m031d_closeout=closed_m031_closeout(),
        mitigation_acceptance=mitigation_acceptance(),
        endpoint_confirmation=endpoint_confirmation(accept_medium=False),
        timeout_policy=timeout_policy(),
    )

    assert report.third_attempt_risk_passed is False
    assert "endpoint_confirmation_missing" in report.blockers
