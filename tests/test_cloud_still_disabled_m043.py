from pathlib import Path

from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.m043_report import load_lambda_m043_report


def test_m043_artifacts_keep_launch_disabled(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = load_lambda_m043_report(paths["m043"])

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_m043_cli_has_no_launch_command():
    cli_text = Path("src/decodilo/cli.py").read_text(encoding="utf-8")

    assert "catalog-rotation" in cli_text
    assert "m043" in cli_text
    assert "m043 launch" not in cli_text
