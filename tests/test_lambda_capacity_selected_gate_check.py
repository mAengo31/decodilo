from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.capacity_selected_gate_check import (
    load_lambda_capacity_selected_gate_check,
)


def test_capacity_selected_gate_check_passes_for_complete_future_review(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_capacity_selected_gate_check(paths["gate_m045"])

    assert report.gate_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.cost_risk_review_status == "passed"
    assert (
        report.operator_approval_status
        == "approved_for_future_m046_capacity_selected_launch_review"
    )
    assert report.response_capture_active is True
    assert report.no_auto_launch_retry is True
    assert report.selected_ssh_key_hash is not None
    assert report.launch_ready is False
    assert report.launch_allowed is False
