from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.capacity_selected_command_preview import (
    load_lambda_capacity_selected_command_preview,
)


def test_capacity_selected_command_preview_non_executable(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_capacity_selected_command_preview(paths["preview_m046"])

    assert report.preview_status == "ready_for_future_m046_capacity_selected_review"
    assert report.executable is False
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert "/tmp/decodilo-lambda-m046" in report.command_preview
    assert "existing-key" not in report.command_preview
    assert report.launch_ready is False
    assert report.launch_allowed is False
