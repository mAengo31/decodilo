from lambda_m029d_helpers import ambiguous_m029_report
from lambda_m031d_helpers import closed_m031_closeout

from decodilo.lambda_cloud.m029_incident_closeout import LambdaM029IncidentCloseoutReport
from decodilo.lambda_cloud.repeated_response_loss_review import (
    build_lambda_repeated_response_loss_review,
)


def _closed_m029_closeout() -> LambdaM029IncidentCloseoutReport:
    return LambdaM029IncidentCloseoutReport(
        incident_status="closed_no_instance_visible",
        closeout_succeeded=True,
        second_launch_blocked=False,
        manual_review_required=False,
    )


def test_two_response_losses_create_future_launch_hold():
    report = build_lambda_repeated_response_loss_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m029e_closeout=_closed_m029_closeout(),
        m031_closeout=closed_m031_closeout(),
    )

    assert report.repeated_response_loss_detected is True
    assert report.review_status == "mitigation_required"
    assert report.future_launch_blocked is True


def test_mitigation_accepted_clears_repeated_loss_blocker_only():
    report = build_lambda_repeated_response_loss_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m029e_closeout=_closed_m029_closeout(),
        m031_closeout=closed_m031_closeout(),
        mitigation_accepted=True,
    )

    assert report.review_status == "mitigation_accepted"
    assert report.future_launch_blocked is False
    assert report.launch_allowed is False


def test_open_closeout_blocks_review():
    open_m029 = LambdaM029IncidentCloseoutReport(
        incident_status="unresolved_requires_manual_review",
        closeout_succeeded=False,
        second_launch_blocked=True,
        manual_review_required=True,
    )

    report = build_lambda_repeated_response_loss_review(
        m029c_report=ambiguous_m029_report(),
        m031_report=ambiguous_m029_report(),
        m029e_closeout=open_m029,
        m031_closeout=closed_m031_closeout(),
    )

    assert report.review_status == "blocked"
    assert "m029_incident_not_closed" in report.blockers
