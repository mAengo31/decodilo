from lambda_m038_helpers import gate_check


def test_lower_cost_gate_check_passes_with_complete_future_approval():
    report = gate_check(approval_complete=True)

    assert report.gate_passed is True
    assert report.effective_launch_timeout_seconds >= 30.0
    assert report.response_capture_active is True
    assert report.status_before_parse is True
    assert report.no_auto_launch_retry is True
    assert report.strand_payload_compatible is True
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.selected_ssh_key_hash is not None
    assert report.selected_ssh_key_hash.startswith("sha256:")
    assert report.launch_ready is False
    assert report.launch_allowed is False
