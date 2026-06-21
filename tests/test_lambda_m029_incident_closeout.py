from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_incident_closeout import closeout_m029_incident
from decodilo.lambda_cloud.m029_incident_report import build_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    build_lambda_m029_manual_console_confirmation,
)


def test_closeout_succeeds_only_for_closed_incident():
    incident = build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(
            lambda_console_checked=True,
            no_instances_visible=True,
            no_pending_instances_visible=True,
            no_alert_instances_visible=True,
        ),
    )

    report = closeout_m029_incident(incident)

    assert report.closeout_succeeded is True
    assert report.second_launch_blocked is False


def test_open_incident_remains_blocked():
    incident = build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(),
    )

    report = closeout_m029_incident(incident)

    assert report.closeout_succeeded is False
    assert "manual_console_confirmation_missing" in report.blockers
