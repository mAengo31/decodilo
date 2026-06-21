from lambda_m038_helpers import command_preview


def test_lower_cost_command_preview_is_non_executable_even_when_ready():
    report = command_preview(approval_complete=True)

    assert report.preview_status == "ready_for_future_m039"
    assert report.executable is False
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.selected_ssh_key_hash is not None
    assert report.selected_ssh_key_hash.startswith("sha256:")
    assert "--execute-real-launch" in report.command
    assert "<future-operator-confirmation-required>" in report.command
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_command_preview_records_blockers():
    report = command_preview(approval_complete=False)

    assert report.preview_status == "blocked"
    assert "operator approval is not marked complete" in report.blockers
