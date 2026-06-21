from lambda_m044h_helpers import write_m044h_inputs

from decodilo.lambda_cloud.m044h_report import load_lambda_m044h_report


def test_m044h_report_passes_for_capacity_history_selector(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_m044h_report(paths["m044h"])

    assert report.report_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert "gpu_1x_h100_pcie" in report.excluded_candidates
    assert (
        report.authorization_status
        == "authorized_for_future_capacity_history_selector_review"
    )
    assert report.gate_check_status == "passed"
    assert report.command_preview_status == (
        "ready_for_future_capacity_history_selector_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
