from lambda_m034d_helpers import (
    confirmed_no_visible_console,
    write_m034c_sent_journal,
    zero_diff,
)

from decodilo.lambda_cloud.launch_failure_journal_recovery import (
    recover_lambda_launch_failure_from_journal,
)
from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.m034_incident_report import build_lambda_m034_incident_report
from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    build_lambda_m034_manual_console_confirmation,
)


def test_m034c_state_plus_console_no_instances_closes(tmp_path):
    journal = write_m034c_sent_journal(tmp_path)
    recovery = recover_lambda_launch_failure_from_journal(
        journal,
        report_path=tmp_path / "missing-report.json",
    )

    report = build_lambda_m034_incident_report(
        source_m034_report_or_journal=journal,
        journal_recovery=recovery,
        discovery_diff=zero_diff(),
        console_confirmation=confirmed_no_visible_console(),
    )

    assert report.incident_status == "closed_no_instance_visible"
    assert report.future_launch_blocked is True
    assert report.crash_safe_diagnostics_required is True
    assert report.transport_error_persisted is False


def test_missing_console_confirmation_unresolved(tmp_path):
    journal = write_m034c_sent_journal(tmp_path)
    recovery = recover_lambda_launch_failure_from_journal(journal)

    report = build_lambda_m034_incident_report(
        source_m034_report_or_journal=journal,
        journal_recovery=recovery,
        discovery_diff=zero_diff(),
        console_confirmation=build_lambda_m034_manual_console_confirmation(),
    )

    assert report.incident_status == "unresolved_requires_manual_review"


def test_ambiguous_candidate_unresolved(tmp_path):
    journal = write_m034c_sent_journal(tmp_path)
    recovery = recover_lambda_launch_failure_from_journal(journal)

    report = build_lambda_m034_incident_report(
        source_m034_report_or_journal=journal,
        journal_recovery=recovery,
        discovery_diff=LambdaM034DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=1,
            possible_owned_candidates=[{"id": "fake-i-a", "status": "running"}],
            confidence="possible_instance_created",
        ),
        console_confirmation=confirmed_no_visible_console(),
    )

    assert report.incident_status == "unresolved_requires_manual_review"
