from lambda_m041_helpers import accepted_decision, declined_decision

from decodilo.lambda_cloud.wait_for_live_availability_plan import (
    build_lambda_wait_for_live_availability_plan,
)


def test_declined_risk_builds_wait_plan():
    report = build_lambda_wait_for_live_availability_plan(declined_decision())

    assert report.plan_status == "wait_for_live_availability"
    assert report.no_mutation is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_accepted_risk_wait_plan_not_applicable():
    report = build_lambda_wait_for_live_availability_plan(accepted_decision())

    assert report.plan_status == "not_applicable"
    assert "operator_accepted_catalog_availability_risk" in report.blockers
