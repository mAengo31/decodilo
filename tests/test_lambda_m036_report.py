from lambda_m036_helpers import endpoint_upgrade, lower_cost_review, strategy_decision

from decodilo.lambda_cloud.m036_report import build_lambda_m036_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight
from decodilo.lambda_cloud.support_confirmation_request import (
    build_lambda_support_confirmation_request,
)


def test_m036_report_builds_with_complete_evidence_and_keeps_flags_false():
    report = build_lambda_m036_report(
        support_request=build_lambda_support_confirmation_request(),
        lower_cost_shape_review=lower_cost_review(),
        strategy_decision=strategy_decision(),
        endpoint_confidence_upgrade=endpoint_upgrade(),
    )

    assert report.report_passed is True
    assert report.strategy_decision.status == "reauthorize_lower_cost_shape_before_next_launch"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m036_report_can_represent_missing_support_response_without_faking_it():
    report = build_lambda_m036_report(
        support_request=build_lambda_support_confirmation_request(),
        lower_cost_shape_review=lower_cost_review(),
    )

    assert report.report_passed is True
    assert report.support_response is None
    assert report.strategy_decision.status == "require_more_support_evidence"
    assert "support_confirmation_response_missing" in report.blockers


def test_m036_report_is_included_in_preflight_but_non_launchable():
    m036 = build_lambda_m036_report(
        support_request=build_lambda_support_confirmation_request(),
        lower_cost_shape_review=lower_cost_review(),
    )

    report = run_lambda_preflight(m036_report=m036)

    assert report.m036_support_confirmation_summary is not None
    assert (
        report.m036_support_confirmation_summary["strategy_decision"]
        == "require_more_support_evidence"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
