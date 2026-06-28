from __future__ import annotations

import pytest
from lambda_m080_helpers import safe_diloco_discovery_kwargs

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    LambdaDilocoSyntheticCommandDiscovery,
    discover_lambda_diloco_synthetic_command,
)


def test_diloco_synthetic_discovery_finds_local_diloco_smoke_command():
    discovery = discover_lambda_diloco_synthetic_command(source_root=".")

    assert discovery.discovery_status == "found_safe_diloco_synthetic_command"
    assert discovery.local_introspection_passed is True
    assert discovery.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "diloco-smoke",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-diloco-smoke.json",
    ]
    assert discovery.learners == 1
    assert discovery.sync_rounds == 1
    assert discovery.max_steps == 1
    assert discovery.no_real_training is True
    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False


def test_diloco_synthetic_discovery_can_represent_safe_future_command():
    discovery = LambdaDilocoSyntheticCommandDiscovery(**safe_diloco_discovery_kwargs())

    assert discovery.no_real_training is True
    assert discovery.no_downloads is True
    assert discovery.gpu_required is False


def test_diloco_synthetic_discovery_rejects_reused_learner_syncer_smoke():
    with pytest.raises(ValueError, match="beyond learner-syncer-smoke"):
        LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="found_safe_diloco_synthetic_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "learner-syncer-smoke"],
            timeout_seconds=120,
        )


def test_diloco_synthetic_discovery_rejects_unsafe_found_command():
    kwargs = safe_diloco_discovery_kwargs()
    kwargs["no_external_network"] = False

    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaDilocoSyntheticCommandDiscovery(**kwargs)
