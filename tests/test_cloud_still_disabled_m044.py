from pathlib import Path

from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.m044_report import load_lambda_m044_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m044_artifacts_keep_launch_disabled(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = load_lambda_m044_report(paths["m044"])

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_m044_cli_has_no_launch_command():
    cli_text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "catalog-rotation" in cli_text
    assert "m044" in cli_text
    assert "m044 launch" not in cli_text


def test_m044_preflight_summary_loads_without_enabling_launch(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = run_lambda_preflight(m044_report=paths["m044"])

    assert report.m044_catalog_rotation_summary is not None
    assert (
        report.m044_catalog_rotation_summary["decision_status"]
        == "authorize_future_m045_catalog_rotation_launch_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False
