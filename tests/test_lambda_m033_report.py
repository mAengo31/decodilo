from lambda_m033_helpers import (
    capture_lock,
    correlation_plan,
    endpoint_confirmation,
    reconciliation_plan,
    risk_review,
    third_attempt_authorization,
    third_attempt_go_no_go,
    timeout_policy,
)

from decodilo.lambda_cloud.m033_report import build_lambda_m033_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m033_report_builds_non_launchable_future_review_package():
    report = build_lambda_m033_report(
        endpoint_confirmation=endpoint_confirmation(),
        response_capture_settings_lock=capture_lock(),
        timeout_policy=timeout_policy(),
        risk_review=risk_review(),
        correlation_plan=correlation_plan(),
        reconciliation_plan=reconciliation_plan(),
        m034_authorization=third_attempt_authorization(),
        go_no_go=third_attempt_go_no_go(),
    )

    assert report.report_passed is True
    assert report.m034_authorization.status == (
        "authorized_for_future_m034_third_launch_attempt"
    )
    assert report.go_no_go.status == "go_for_future_m034_third_launch_review"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lambda_preflight_includes_m033_status_but_stays_disabled():
    report = build_lambda_m033_report(
        endpoint_confirmation=endpoint_confirmation(),
        response_capture_settings_lock=capture_lock(),
        timeout_policy=timeout_policy(),
        risk_review=risk_review(),
        correlation_plan=correlation_plan(),
        reconciliation_plan=reconciliation_plan(),
        m034_authorization=third_attempt_authorization(),
        go_no_go=third_attempt_go_no_go(),
    )
    preflight = run_lambda_preflight(
        launch_plan=None,
        teardown_plan=None,
        ledger=None,
        m033_report=report,
    )

    assert preflight.m033_third_attempt_summary is not None
    assert preflight.m033_third_attempt_summary["authorization_status"] == (
        "authorized_for_future_m034_third_launch_attempt"
    )
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
