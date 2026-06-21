from lambda_m044h_helpers import write_m044h_inputs

from decodilo.lambda_cloud.capacity_history_selector_command_preview import (
    load_lambda_capacity_history_selector_command_preview,
)


def test_capacity_history_selector_command_preview_non_executable(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_capacity_history_selector_command_preview(
        paths["preview_m044h"]
    )

    assert report.preview_status == "ready_for_future_capacity_history_selector_review"
    assert report.executable is False
    assert report.hardcoded_shape_outside_selector_output is False
    assert "gpu_8x_a100_80gb_sxm4" not in report.command_preview
    assert "gpu_1x_h100_pcie" not in report.command_preview
    assert report.launch_ready is False
    assert report.launch_allowed is False
