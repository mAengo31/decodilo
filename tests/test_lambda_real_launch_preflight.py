from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.future_launch_hold import LambdaFutureLaunchHoldReport
from decodilo.lambda_cloud.real_launch_preflight import run_m029_launch_preflight


def test_real_launch_preflight_passes_fake_candidate(tmp_path):
    fx = m029_fixture(tmp_path)
    report = run_m029_launch_preflight(arming_report=fx["arming"])

    assert report.preflight_passed is True
    assert report.fake_server_mode is True
    assert report.launch_allowed is False


def test_real_launch_preflight_blocks_future_launch_hold(tmp_path):
    fx = m029_fixture(tmp_path)
    report = run_m029_launch_preflight(
        arming_report=fx["arming"],
        future_launch_hold=LambdaFutureLaunchHoldReport(
            future_launch_hold_active=True,
            hold_reasons=["repeated_response_loss_unmitigated"],
            required_clearance_items=["complete mitigation"],
            incident_closeout_required=False,
            repeated_response_loss_review_required=True,
            root_cause_mitigation_required=True,
        ),
    )

    assert report.preflight_passed is False
    assert "future_launch_hold_active" in report.blockers
    assert report.launch_allowed is False
