from lambda_m031d_helpers import ambiguous_m031_report

from decodilo.lambda_cloud.m031_discovery_diff import LambdaM031DiscoveryDiffReport
from decodilo.lambda_cloud.m031_incident_closeout import closeout_m031_incident
from decodilo.lambda_cloud.m031_incident_report import build_lambda_m031_incident_report
from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    build_lambda_m031_manual_console_confirmation,
)


def test_closeout_succeeds_only_for_closed_incident_but_global_hold_remains():
    incident = build_lambda_m031_incident_report(
        source_m031_report="/tmp/report.json",
        m031_report=ambiguous_m031_report(),
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m031_manual_console_confirmation(
            lambda_console_checked=True,
            no_instances_visible=True,
            no_pending_instances_visible=True,
            no_alert_instances_visible=True,
            no_owned_instance_found=True,
        ),
    )

    report = closeout_m031_incident(incident)

    assert report.closeout_succeeded is True
    assert report.incident_future_launch_blocked is False
    assert report.global_future_launch_blocked is True
    assert "repeated_response_loss_review_required" in report.blockers


def test_open_incident_remains_blocked():
    incident = build_lambda_m031_incident_report(
        source_m031_report="/tmp/report.json",
        m031_report=ambiguous_m031_report(),
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m031_manual_console_confirmation(),
    )

    report = closeout_m031_incident(incident)

    assert report.closeout_succeeded is False
    assert "manual_console_confirmation_missing" in report.blockers
