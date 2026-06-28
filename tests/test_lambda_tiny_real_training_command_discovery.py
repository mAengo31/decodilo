from __future__ import annotations

import pytest

from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    LambdaTinyRealTrainingCommandDiscovery,
    discover_lambda_tiny_real_training_command,
)


def test_tiny_real_training_discovery_finds_verified_command():
    discovery = discover_lambda_tiny_real_training_command(source_root=".")

    assert discovery.discovery_status == "found_safe_tiny_real_training_command"
    assert discovery.local_smoke_passed is True
    assert discovery.training_attempted is True
    assert discovery.real_training_mechanics_exercised is True
    assert discovery.torch_required is False
    assert discovery.gpu_required is False
    assert discovery.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "tiny-real-training-smoke",
        "--synthetic",
        "--model",
        "tiny-linear",
        "--steps",
        "1",
        "--optimizer",
        "adamw",
        "--out",
        "/tmp/decodilo-tiny-real-training-smoke.json",
    ]


def test_tiny_real_training_discovery_rejects_unsafe_found_flags():
    with pytest.raises(ValueError, match="bad flags"):
        LambdaTinyRealTrainingCommandDiscovery(
            discovery_status="found_safe_tiny_real_training_command",
            argv_tokens=["python3"],
            local_smoke_passed=True,
            training_attempted=True,
            real_training_mechanics_exercised=True,
            no_external_network=False,
            bounded_runtime=True,
            bounded_output=True,
        )
