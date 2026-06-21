from pathlib import Path

from lambda_m041_helpers import write_m041_inputs

from decodilo.lambda_cloud.catalog_availability_command_preview import (
    load_lambda_catalog_availability_command_preview,
)
from decodilo.lambda_cloud.catalog_availability_gate_check import (
    load_lambda_catalog_availability_gate_check,
)
from decodilo.lambda_cloud.catalog_availability_m042_authorization import (
    load_lambda_catalog_availability_m042_authorization,
)
from decodilo.lambda_cloud.m041_report import load_lambda_m041_report


def test_m041_artifacts_keep_launch_disabled(tmp_path):
    paths = write_m041_inputs(tmp_path)
    reports = [
        load_lambda_catalog_availability_m042_authorization(paths["m042"]),
        load_lambda_catalog_availability_gate_check(paths["gate"]),
        load_lambda_catalog_availability_command_preview(paths["preview"]),
        load_lambda_m041_report(paths["m041"]),
    ]

    for report in reports:
        assert report.launch_ready is False
        assert report.launch_allowed is False
        assert report.billable_action_performed is False
        assert report.real_mutation_enabled is False


def test_m041_cli_has_no_catalog_availability_launch_command():
    cli_text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "catalog-availability" in cli_text
    assert "authorize-m042" in cli_text
    assert "catalog-availability launch" not in cli_text
