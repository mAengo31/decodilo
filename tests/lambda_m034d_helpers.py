from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.launch_failure_journal_recovery import (
    recover_lambda_launch_failure_from_journal,
)
from decodilo.lambda_cloud.m034_discovery_diff import LambdaM034DiscoveryDiffReport
from decodilo.lambda_cloud.m034_incident_closeout import closeout_m034_incident
from decodilo.lambda_cloud.m034_incident_report import build_lambda_m034_incident_report
from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    build_lambda_m034_manual_console_confirmation,
)
from decodilo.lambda_cloud.real_launch_journal import LambdaM029LaunchJournal


def write_m034c_sent_journal(tmp_path: Path) -> Path:
    journal = LambdaM029LaunchJournal(tmp_path / "journal.jsonl", run_id="m034c-test")
    journal.append("m029_preflight_started")
    journal.append("m029_arming_succeeded")
    journal.append("m029_launch_request_about_to_send")
    journal.append("m029_launch_request_sent")
    return journal.path


def zero_diff() -> LambdaM034DiscoveryDiffReport:
    return LambdaM034DiscoveryDiffReport(
        pre_instance_count=0,
        post_instance_count=0,
        closeout_instance_count=0,
        confidence="high_no_instance_created",
    )


def confirmed_no_visible_console():
    return build_lambda_m034_manual_console_confirmation(
        lambda_console_checked=True,
        no_instances_visible=True,
        no_pending_instances_visible=True,
        no_alert_instances_visible=True,
        no_owned_instance_found=True,
    )


def closed_m034_incident(tmp_path: Path):
    journal = write_m034c_sent_journal(tmp_path)
    recovery = recover_lambda_launch_failure_from_journal(
        journal,
        report_path=tmp_path / "missing-report.json",
    )
    return build_lambda_m034_incident_report(
        source_m034_report_or_journal=journal,
        journal_recovery=recovery,
        discovery_diff=zero_diff(),
        console_confirmation=confirmed_no_visible_console(),
    )


def closed_m034_closeout(tmp_path: Path):
    return closeout_m034_incident(closed_m034_incident(tmp_path))
