from __future__ import annotations

from lambda_m078_helpers import safe_next_discovery_kwargs

from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    LambdaNextSyntheticExperimentDiscovery,
    write_lambda_next_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.next_synthetic_experiment_policy import (
    build_lambda_next_synthetic_experiment_policy_from_path,
)


def test_next_synthetic_experiment_policy_blocks_without_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            blockers=["no_safe_next_synthetic_experiment_command_found"],
        ),
    )

    policy = build_lambda_next_synthetic_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_next_synthetic_experiment_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_next_synthetic_experiment_policy_accepts_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(**safe_next_discovery_kwargs()),
    )

    policy = build_lambda_next_synthetic_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.one_bounded_synthetic_experiment_command is True
    assert policy.no_real_training is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_next_synthetic_experiment_policy_rejects_blocked_discovery(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            blockers=[
                "next_synthetic_experiment_network_allowed",
                "next_synthetic_experiment_download_allowed",
                "next_synthetic_experiment_package_install_allowed",
                "next_synthetic_experiment_training_allowed",
                "next_synthetic_experiment_background_allowed",
            ],
        ),
    )

    policy = build_lambda_next_synthetic_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_next_synthetic_experiment_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
