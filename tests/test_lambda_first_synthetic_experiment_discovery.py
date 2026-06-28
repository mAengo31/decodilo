from __future__ import annotations

import pytest

from decodilo.lambda_cloud.first_synthetic_experiment_discovery import (
    LambdaFirstSyntheticExperimentDiscovery,
    discover_lambda_first_synthetic_experiment_command,
)

EXPECTED_REMOTE_ARGV = [
    "env",
    "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "synthetic-experiment",
    "--synthetic",
    "--max-steps",
    "1",
    "--out",
    "/tmp/decodilo-synthetic-experiment.json",
]


def test_first_synthetic_experiment_discovery_finds_safe_command():
    discovery = discover_lambda_first_synthetic_experiment_command(source_root=".")

    assert (
        discovery.discovery_status
        == "found_safe_first_synthetic_experiment_command"
    )
    assert discovery.local_introspection_passed is True
    assert discovery.argv_tokens == EXPECTED_REMOTE_ARGV
    assert discovery.synthetic_only is True
    assert discovery.no_external_network is True
    assert discovery.no_package_install is True
    assert discovery.no_downloads is True
    assert discovery.no_real_training is True
    assert discovery.no_background_process is True
    assert discovery.gpu_required is False
    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False


def test_first_synthetic_experiment_discovery_can_represent_safe_command():
    discovery = LambdaFirstSyntheticExperimentDiscovery(
        discovery_status="found_safe_first_synthetic_experiment_command",
        command_category="dev_synthetic_experiment_one_step",
        argv_tokens=EXPECTED_REMOTE_ARGV,
        local_introspection_passed=True,
        timeout_seconds=120,
        generated_workdir_path="/tmp/decodilo-synthetic-experiment",
    )

    assert discovery.no_real_training is True
    assert discovery.no_downloads is True
    assert discovery.gpu_required is False


def test_first_synthetic_experiment_discovery_rejects_unsafe_found_command():
    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="found_safe_first_synthetic_experiment_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "train"],
            timeout_seconds=120,
            no_real_training=False,
        )
