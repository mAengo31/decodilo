from __future__ import annotations

from lambda_m082_helpers import safe_optimizer_discovery_kwargs

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    LambdaDilocoOptimizerCommandDiscovery,
    write_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    build_lambda_diloco_optimizer_policy_from_path,
)


def test_diloco_optimizer_policy_blocks_without_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_diloco_optimizer_command_discovery(
        discovery_path,
        LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="no_safe_diloco_optimizer_command_found",
            blockers=["no_safe_diloco_optimizer_command_found"],
        ),
    )

    policy = build_lambda_diloco_optimizer_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_diloco_optimizer_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_diloco_optimizer_policy_passes_for_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_diloco_optimizer_command_discovery(
        discovery_path,
        LambdaDilocoOptimizerCommandDiscovery(**safe_optimizer_discovery_kwargs()),
    )

    policy = build_lambda_diloco_optimizer_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.inner_optimizer == "adamw"
    assert policy.outer_optimizer == "nesterov"
    assert policy.no_real_training is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
