from lambda_m038_helpers import command_preview


def test_m039_command_preview_ready_is_non_executable():
    report = command_preview(approval_complete=True)

    assert report.preview_status == "ready_for_future_m039"
    assert report.executable is False
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.selected_ssh_key_hash is not None
    assert report.selected_ssh_key_hash.startswith("sha256:")
    assert report.response_loss_controls_ref.endswith(
        "decodilo-lambda-strand-response-loss-controls.json"
    )
    assert "--execute-real-launch" in report.command
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False
