from __future__ import annotations

import pytest
from lambda_m078_helpers import safe_next_discovery_kwargs

from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    LambdaNextSyntheticExperimentDiscovery,
    discover_lambda_next_synthetic_experiment_command,
)


def test_next_synthetic_experiment_discovery_finds_learner_syncer_smoke():
    discovery = discover_lambda_next_synthetic_experiment_command(source_root=".")

    assert (
        discovery.discovery_status
        == "found_safe_next_synthetic_experiment_command"
    )
    assert discovery.local_introspection_passed is True
    assert discovery.command_category == "dev_learner_syncer_smoke_one_step"
    assert discovery.argv_tokens == safe_next_discovery_kwargs()["argv_tokens"]
    assert discovery.no_real_training is True
    assert discovery.no_downloads is True
    assert discovery.no_package_install is True
    assert discovery.no_external_network is True
    assert discovery.no_background_process is True
    assert discovery.gpu_required is False
    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False


def test_next_synthetic_experiment_discovery_can_represent_safe_future_command():
    discovery = LambdaNextSyntheticExperimentDiscovery(**safe_next_discovery_kwargs())

    assert discovery.no_real_training is True
    assert discovery.no_downloads is True
    assert discovery.gpu_required is False


def test_next_synthetic_experiment_discovery_rejects_reused_synthetic_experiment():
    with pytest.raises(ValueError, match="beyond synthetic-experiment"):
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="found_safe_next_synthetic_experiment_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "synthetic-experiment"],
            timeout_seconds=120,
        )


def test_next_synthetic_experiment_discovery_rejects_unsafe_found_command():
    kwargs = safe_next_discovery_kwargs()
    kwargs["no_external_network"] = False

    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaNextSyntheticExperimentDiscovery(**kwargs)
