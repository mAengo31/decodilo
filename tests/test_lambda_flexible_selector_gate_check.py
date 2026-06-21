from lambda_m044g_helpers import write_m044g_inputs

from decodilo.lambda_cloud.flexible_selector_gate_check import (
    load_lambda_flexible_selector_gate_check,
)


def test_flexible_selector_gate_check_passes(tmp_path):
    paths = write_m044g_inputs(tmp_path)
    report = load_lambda_flexible_selector_gate_check(paths["gate"])

    assert report.gate_passed is True
    assert report.selected_candidate is not None
    assert report.selected_candidate_reason
    assert report.fixed_shape_path_used is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_flexible_selector_gate_check_blocks_when_authorization_blocks(tmp_path):
    paths = write_m044g_inputs(tmp_path, approve=False)
    report = load_lambda_flexible_selector_gate_check(paths["gate"])

    assert report.gate_passed is False
    assert "flexible_selector_authorization_not_ready" in report.blockers
