from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_incident_report import build_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    build_lambda_m029_manual_console_confirmation,
)


def test_m029c_state_plus_console_no_instances_closes():
    report = build_lambda_m029_incident_report(
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

    assert report.incident_status == "closed_no_instance_visible"
    assert report.second_launch_blocked is False


def test_missing_console_confirmation_unresolved():
    report = build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(),
    )

    assert report.incident_status == "unresolved_requires_manual_review"
    assert report.second_launch_blocked is True


def test_ambiguous_candidate_unresolved():
    report = build_lambda_m029_incident_report(
        source_m029_report="/tmp/report.json",
        m029_report=ambiguous_m029_report(),
        discovery_diff=LambdaM029DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=1,
            possible_owned_candidates=[{"instance_id": "fake-i-a", "status": "running"}],
            confidence="possible_instance_created",
        ),
        console_confirmation=build_lambda_m029_manual_console_confirmation(
            lambda_console_checked=True,
            no_instances_visible=True,
            no_pending_instances_visible=True,
            no_alert_instances_visible=True,
        ),
    )

    assert report.incident_status == "unresolved_requires_manual_review"
