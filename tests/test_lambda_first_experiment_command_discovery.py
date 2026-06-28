from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    discover_lambda_first_experiment_command,
)


def test_first_experiment_command_discovery_uses_local_cli_introspection() -> None:
    report = discover_lambda_first_experiment_command(source_root=Path.cwd())

    assert report.discovery_status == "safe_experiment_command_found"
    assert report.local_validation_passed is True
    assert report.argv_tokens[:6] == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
    ]
    assert "ci-profile-report" in report.argv_tokens
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_package_install is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
