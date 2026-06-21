from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m031d_helpers import closed_m031_incident

from decodilo.lambda_cloud.future_launch_hold import build_lambda_future_launch_hold
from decodilo.lambda_cloud.launch_response_loss_root_cause import (
    LambdaLaunchResponseLossRootCauseReport,
)
from decodilo.lambda_cloud.m031_discovery_diff import LambdaM031DiscoveryDiffReport
from decodilo.lambda_cloud.m031_incident_report import build_lambda_m031_incident_report
from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    build_lambda_m031_manual_console_confirmation,
)
from decodilo.lambda_cloud.repeated_response_loss_review import (
    LambdaRepeatedResponseLossReviewReport,
)


def _review(blocked: bool) -> LambdaRepeatedResponseLossReviewReport:
    return LambdaRepeatedResponseLossReviewReport(
        repeated_response_loss_detected=True,
        attempts_analyzed=2,
        response_loss_count=2,
        successful_launch_response_count=0,
        m029_incident_closed=True,
        m031_incident_closed=True,
        root_cause=LambdaLaunchResponseLossRootCauseReport(
            repeated_response_loss_detected=True,
            attempts_analyzed=2,
            response_loss_count=2,
            successful_launch_response_count=0,
            mitigation_accepted=not blocked,
            future_launch_blocked=blocked,
        ),
        review_status="mitigation_required" if blocked else "mitigation_accepted",
        mitigation_accepted=not blocked,
        future_launch_blocked=blocked,
    )


def test_open_m031_incident_keeps_hold_active():
    incident = build_lambda_m031_incident_report(
        source_m031_report="/tmp/report.json",
        m031_report=ambiguous_m029_report(),
        discovery_diff=LambdaM031DiscoveryDiffReport(
            pre_instance_count=0,
            post_instance_count=0,
            confidence="high_no_instance_created",
        ),
        console_confirmation=build_lambda_m031_manual_console_confirmation(),
    )

    hold = build_lambda_future_launch_hold(
        m031_incident_report=incident,
        repeated_response_loss_review=_review(blocked=False),
    )

    assert hold.future_launch_hold_active is True
    assert "m031_incident_open" in hold.hold_reasons


def test_repeated_loss_unmitigated_keeps_hold_active():
    hold = build_lambda_future_launch_hold(
        m031_incident_report=closed_m031_incident(),
        repeated_response_loss_review=_review(blocked=True),
    )

    assert hold.future_launch_hold_active is True
    assert "repeated_response_loss_unmitigated" in hold.hold_reasons


def test_closed_and_mitigated_clears_hold_but_not_launch_flags():
    hold = build_lambda_future_launch_hold(
        m031_incident_report=closed_m031_incident(),
        repeated_response_loss_review=_review(blocked=False),
    )

    assert hold.future_launch_hold_active is False
    assert hold.launch_ready is False
    assert hold.launch_allowed is False
