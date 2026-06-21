from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m029_discovery_diff import LambdaM029DiscoveryDiffReport
from decodilo.lambda_cloud.m029_incident_report import build_lambda_m029_incident_report
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    build_lambda_m029_manual_console_confirmation,
)
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingReport
from decodilo.lambda_cloud.real_launch_preflight import run_m029_launch_preflight


def test_preflight_blocks_open_previous_incident():
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

    preflight = run_m029_launch_preflight(
        arming_report=LambdaM029ArmingReport(
            run_id="run",
            arming_passed=False,
            blockers=["arming token missing"],
        ),
        previous_incident=incident,
    )

    assert "open_m029_incident_blocks_second_launch" in preflight.blockers
    assert preflight.launch_allowed is False
