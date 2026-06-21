from lambda_m031d_helpers import ambiguous_m031_report

from decodilo.lambda_cloud.m031_discovery_diff import LambdaM031DiscoveryDiffReport
from decodilo.lambda_cloud.m031_incident_report import build_lambda_m031_incident_report
from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    build_lambda_m031_manual_console_confirmation,
)
from decodilo.lambda_cloud.m031_second_attempt_blocker import (
    build_lambda_m031_second_attempt_blocker,
)


def test_open_m031_incident_blocks_future_launch():
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

    report = build_lambda_m031_second_attempt_blocker(incident)

    assert report.incident_blocker_cleared is False
    assert report.global_future_launch_blocked is True
    assert report.launch_allowed is False
