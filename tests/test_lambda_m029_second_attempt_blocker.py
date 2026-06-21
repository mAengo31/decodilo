from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_incident_report import build_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    build_lambda_m029_manual_console_confirmation,
)
from decodilo.lambda_cloud.m029_second_attempt_blocker import (
    build_lambda_m029_second_attempt_blocker,
)


def test_open_incident_blocks_second_launch():
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

    report = build_lambda_m029_second_attempt_blocker(incident)

    assert report.second_attempt_allowed is False
    assert report.launch_allowed is False


def test_closed_incident_clears_incident_blocker_only():
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

    report = build_lambda_m029_second_attempt_blocker(incident)

    assert report.second_attempt_allowed is True
    assert report.launch_ready is False
