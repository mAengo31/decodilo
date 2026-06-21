from lambda_m044h_helpers import write_m044h_inputs

from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    load_lambda_capacity_history_selector_gate_check,
)


def test_capacity_history_selector_gate_check_passes(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_capacity_history_selector_gate_check(paths["gate_m044h"])

    assert report.gate_passed is True
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.selected_candidate_has_recent_capacity_failure is False
    assert "gpu_1x_h100_pcie" in report.recent_capacity_failure_excluded_candidates
    assert report.launch_ready is False
    assert report.launch_allowed is False
