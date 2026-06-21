from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.catalog_rotation_command_preview import (
    build_lambda_catalog_rotation_command_preview_from_path,
)


def test_catalog_rotation_command_preview_ready_non_executable(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_catalog_rotation_command_preview_from_path(
        paths["authorization_m045"]
    )

    assert report.preview_status == "ready_for_future_m045"
    assert report.executable is False
    assert "gpu_8x_a100_80gb_sxm4" not in " ".join(report.command_preview)
    assert "ssh_key_names" not in " ".join(report.command_preview)
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_command_preview_blocked_when_not_authorized(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False, decline_wait=True)
    report = build_lambda_catalog_rotation_command_preview_from_path(
        paths["authorization_m045"]
    )

    assert report.preview_status == "blocked"
    assert report.command_preview == []
