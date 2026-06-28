from __future__ import annotations

from lambda_m080_helpers import safe_diloco_discovery_kwargs

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    LambdaDilocoSyntheticCommandDiscovery,
    write_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    build_lambda_diloco_synthetic_policy_from_path,
)


def test_diloco_synthetic_policy_blocks_when_no_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="no_safe_diloco_synthetic_command_found",
            blockers=["no_safe_diloco_synthetic_command_found"],
        ),
    )

    policy = build_lambda_diloco_synthetic_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_diloco_synthetic_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_diloco_synthetic_policy_passes_safe_future_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery(**safe_diloco_discovery_kwargs()),
    )

    policy = build_lambda_diloco_synthetic_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.one_bounded_diloco_synthetic_command is True
    assert policy.learners == 1
    assert policy.sync_rounds == 1
    assert policy.max_steps == 1
    assert policy.no_real_training is True


def test_diloco_synthetic_policy_rejects_non_one_step_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    kwargs = safe_diloco_discovery_kwargs()
    kwargs["max_steps"] = 2
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery.model_construct(**kwargs),
    )

    policy = build_lambda_diloco_synthetic_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "diloco_synthetic_max_steps_not_one" in policy.blockers
