from lambda_m044g_helpers import write_m044g_inputs

from decodilo.lambda_cloud.flexible_selector_command_preview import (
    load_lambda_flexible_selector_command_preview,
)


def test_flexible_selector_command_preview_is_non_executable(tmp_path):
    paths = write_m044g_inputs(tmp_path)
    report = load_lambda_flexible_selector_command_preview(paths["preview"])

    assert report.preview_status == "ready_for_future_flexible_selector_review"
    assert report.executable is False
    assert report.includes_raw_ssh_key_name is False
    assert report.hardcoded_shape_outside_selector_output is False
    assert "--flexible-selector-authorization" in report.command_preview
    assert "gpu_1x_h100_pcie" not in report.command_preview
    assert "gpu_8x_a100_80gb_sxm4" not in report.command_preview
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_flexible_selector_command_preview_blocks_without_selector_authorization(tmp_path):
    paths = write_m044g_inputs(tmp_path, approve=False)
    report = load_lambda_flexible_selector_command_preview(paths["preview"])

    assert report.preview_status == "blocked"
    assert report.command_preview == []
