from lambda_m041_helpers import write_m041_inputs

from decodilo.lambda_cloud.catalog_availability_command_preview import (
    build_lambda_catalog_availability_command_preview_from_paths,
)


def test_catalog_availability_command_preview_ready_and_non_executable(tmp_path):
    paths = write_m041_inputs(tmp_path)

    report = build_lambda_catalog_availability_command_preview_from_paths(
        m042_authorization=paths["m042"],
        gate_check=paths["gate"],
    )

    assert report.preview_status == "ready_for_future_m042"
    assert report.executable is False
    assert "gpu_1x_h100_pcie" not in report.command
    assert "<future-M042-operator-confirmation-required>" in report.command
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_availability_command_preview_blocks_when_gate_blocks(tmp_path):
    paths = write_m041_inputs(tmp_path)
    paths["gate"].write_text(
        paths["gate"].read_text(encoding="utf-8").replace(
            '"gate_passed": true',
            '"gate_passed": false',
        ),
        encoding="utf-8",
    )

    report = build_lambda_catalog_availability_command_preview_from_paths(
        m042_authorization=paths["m042"],
        gate_check=paths["gate"],
    )

    assert report.preview_status == "blocked"
