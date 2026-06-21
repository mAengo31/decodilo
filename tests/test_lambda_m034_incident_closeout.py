from lambda_m034d_helpers import closed_m034_incident

from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.m034_incident_closeout import closeout_m034_incident
from decodilo.lambda_cloud.m034_incident_report import build_lambda_m034_incident_report
from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    build_lambda_m034_manual_console_confirmation,
)


def test_m034_closeout_succeeds_but_hold_remains(tmp_path):
    report = closeout_m034_incident(closed_m034_incident(tmp_path))

    assert report.closeout_succeeded is True
    assert report.incident_future_launch_blocked is False
    assert report.future_launch_hold_active is True
    assert "crash_safe_diagnostics_hardening_required" in report.blockers


def test_m034_closeout_requires_console_confirmation():
    incident = build_lambda_m034_incident_report(
        source_m034_report_or_journal="/tmp/journal.jsonl",
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m034_manual_console_confirmation(),
    )

    report = closeout_m034_incident(incident)

    assert report.closeout_succeeded is False
    assert "manual_console_confirmation_missing" in report.blockers
