from lambda_m029d_helpers import ambiguous_m029_report

from decodilo.lambda_cloud.m031_discovery_diff import LambdaM031DiscoveryDiffReport
from decodilo.lambda_cloud.m031_incident_closeout import closeout_m031_incident
from decodilo.lambda_cloud.m031_incident_report import build_lambda_m031_incident_report
from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    build_lambda_m031_manual_console_confirmation,
)


def ambiguous_m031_report():
    return ambiguous_m029_report()


def closed_m031_incident():
    return build_lambda_m031_incident_report(
        source_m031_report="/tmp/m031-report.json",
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


def closed_m031_closeout():
    return closeout_m031_incident(closed_m031_incident())
