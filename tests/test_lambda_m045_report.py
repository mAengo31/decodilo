from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.m045_report import load_lambda_m045_report


def test_m045_report_passes_for_accepted_future_review(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_m045_report(paths["m045"])

    assert report.report_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.cost_risk_review_status == "passed"
    assert (
        report.operator_approval_status
        == "approved_for_future_m046_capacity_selected_launch_review"
    )
    assert (
        report.m046_authorization_status
        == "authorized_for_future_m046_capacity_selected_launch_review"
    )
    assert report.gate_check_status == "passed"
    assert report.command_preview_status == "ready_for_future_m046_capacity_selected_review"
    assert report.decision_status == "authorize_future_m046_capacity_selected_launch_review"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m045_report_handles_wait_path(tmp_path):
    paths = write_m045_inputs(tmp_path, approve=False, decline_wait=True)
    report = load_lambda_m045_report(paths["m045"])

    assert report.decision_status == "wait_for_live_availability"
    assert report.future_launch_candidate is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
