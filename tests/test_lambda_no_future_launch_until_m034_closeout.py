from lambda_m029_helpers import m029_fixture
from lambda_m034d_helpers import closed_m034_incident

from decodilo.lambda_cloud.m034_future_launch_hold import (
    build_lambda_m034_future_launch_hold,
)
from decodilo.lambda_cloud.real_launch_preflight import run_m029_launch_preflight


def test_m034_future_hold_blocks_preflight(tmp_path):
    fx = m029_fixture(tmp_path)
    hold = build_lambda_m034_future_launch_hold(
        incident_report=closed_m034_incident(tmp_path / "incident"),
        crash_safe_diagnostics=None,
    )

    report = run_m029_launch_preflight(
        arming_report=fx["arming"],
        m034_future_launch_hold=hold,
    )

    assert report.preflight_passed is False
    assert "m034_future_launch_hold_active" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
