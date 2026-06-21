from lambda_m034d_helpers import closed_m034_incident

from decodilo.lambda_cloud.crash_safe_transport_diagnostics import (
    LambdaCrashSafeTransportDiagnosticsReport,
)
from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.m034_future_launch_hold import (
    build_lambda_m034_future_launch_hold,
)
from decodilo.lambda_cloud.m034_incident_report import build_lambda_m034_incident_report
from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    build_lambda_m034_manual_console_confirmation,
)


def accepted_diagnostics():
    return LambdaCrashSafeTransportDiagnosticsReport(
        diagnostics_hardening_accepted=True,
        transport_error_persisted=True,
        response_capture_persisted=True,
        status_captured_before_parse=True,
        timeout_distinguished=True,
        malformed_or_non_json_distinguished=True,
        no_auto_retry=True,
        secret_scan_passed=True,
    )


def test_closed_incident_without_hardening_keeps_hold_active(tmp_path):
    report = build_lambda_m034_future_launch_hold(
        incident_report=closed_m034_incident(tmp_path),
        crash_safe_diagnostics=None,
    )

    assert report.future_launch_hold_active is True
    assert "crash_safe_diagnostics_not_accepted" in report.hold_reasons
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_closed_incident_and_accepted_hardening_clears_for_future_review(tmp_path):
    report = build_lambda_m034_future_launch_hold(
        incident_report=closed_m034_incident(tmp_path),
        crash_safe_diagnostics=accepted_diagnostics(),
    )

    assert report.future_launch_hold_active is False
    assert report.operator_reapproval_required is True


def test_open_incident_keeps_hold_even_with_hardening():
    incident = build_lambda_m034_incident_report(
        source_m034_report_or_journal="/tmp/journal.jsonl",
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m034_manual_console_confirmation(),
    )

    report = build_lambda_m034_future_launch_hold(
        incident_report=incident,
        crash_safe_diagnostics=accepted_diagnostics(),
    )

    assert report.future_launch_hold_active is True
    assert "m034_incident_open" in report.hold_reasons
