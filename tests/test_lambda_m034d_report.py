from lambda_m034d_helpers import closed_m034_closeout, closed_m034_incident

from decodilo.lambda_cloud.m034_future_launch_hold import (
    build_lambda_m034_future_launch_hold,
)
from decodilo.lambda_cloud.m034d_report import build_lambda_m034d_report


def test_m034d_report_builds_non_launchable(tmp_path):
    incident = closed_m034_incident(tmp_path)
    hold = build_lambda_m034_future_launch_hold(
        incident_report=incident,
        crash_safe_diagnostics=None,
    )

    report = build_lambda_m034d_report(
        incident_report=incident,
        closeout=closed_m034_closeout(tmp_path / "closeout"),
        future_launch_hold=hold,
    )

    assert report.closeout_succeeded is True
    assert report.future_launch_hold_active is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
