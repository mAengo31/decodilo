from __future__ import annotations

import pytest

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    LambdaDilocoOptimizerCommandDiscovery,
    discover_lambda_diloco_optimizer_command,
)


def test_diloco_optimizer_discovery_finds_safe_command():
    report = discover_lambda_diloco_optimizer_command(source_root=".")

    assert report.discovery_status == "found_safe_diloco_optimizer_command"
    assert report.command_category == "dev_diloco_optimizer_smoke_adamw_nesterov_one_step"
    assert report.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "diloco-optimizer-smoke",
        "--synthetic",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-diloco-optimizer-smoke.json",
    ]
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.expected_optimizer_fidelity == "optimizer_semantics_smoke"
    assert report.no_real_training is True
    assert report.no_external_network is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_diloco_optimizer_discovery_rejects_diloco_smoke_as_not_beyond():
    with pytest.raises(ValueError, match="beyond diloco-smoke"):
        LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="found_safe_diloco_optimizer_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "diloco-smoke"],
            timeout_seconds=120,
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
        )
