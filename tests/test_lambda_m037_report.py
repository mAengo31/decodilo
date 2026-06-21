from lambda_m037_helpers import m037_decision

from decodilo.lambda_cloud.m037_report import build_lambda_m037_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m037_report_serializes_and_keeps_flags_false(tmp_path):
    report = build_lambda_m037_report(decision=m037_decision(tmp_path))

    assert report.report_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert "launch_allowed\": true" not in report.to_json()


def test_m037_report_is_included_in_preflight_but_non_launchable(tmp_path):
    report = build_lambda_m037_report(decision=m037_decision(tmp_path))
    preflight = run_lambda_preflight(m037_report=report)

    assert preflight.m037_support_response_summary is not None
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False

