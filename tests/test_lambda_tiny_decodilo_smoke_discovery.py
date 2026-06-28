from __future__ import annotations

from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    discover_lambda_tiny_decodilo_smoke_command,
)


def test_tiny_smoke_discovery_finds_real_command():
    discovery = discover_lambda_tiny_decodilo_smoke_command(source_root=".")

    assert discovery.discovery_status == "found_safe_tiny_smoke_command"
    assert discovery.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "tiny-smoke",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-tiny-smoke.json",
    ]
    assert discovery.no_training is True
    assert discovery.no_downloads is True
    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False
