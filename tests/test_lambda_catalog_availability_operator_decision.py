from lambda_m041_helpers import accepted_decision, declined_decision

from decodilo.lambda_cloud.catalog_availability_operator_decision import (
    build_lambda_catalog_availability_operator_decision,
)
from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    build_lambda_catalog_availability_risk_acceptance,
)


def test_accepted_risk_becomes_future_m042_decision():
    report = accepted_decision()

    assert (
        report.decision_status
        == "accept_catalog_availability_risk_for_future_m042_review"
    )
    assert report.future_m042_review_allowed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_declined_risk_becomes_wait_decision():
    report = declined_decision()

    assert report.decision_status == "wait_for_live_availability"
    assert report.wait_for_live_availability is True


def test_missing_risk_acceptance_is_incomplete():
    risk = build_lambda_catalog_availability_risk_acceptance()
    report = build_lambda_catalog_availability_operator_decision(risk)

    assert report.decision_status == "incomplete"
    assert report.blockers
