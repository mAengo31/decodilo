from __future__ import annotations

from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    LambdaTinyRealTrainingCommandDiscovery,
    discover_lambda_tiny_real_training_command,
    write_lambda_tiny_real_training_command_discovery,
)
from decodilo.lambda_cloud.tiny_real_training_policy import (
    build_lambda_tiny_real_training_policy_from_path,
)


def test_tiny_real_training_policy_passes_for_verified_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_tiny_real_training_command_discovery(
        discovery_path,
        discover_lambda_tiny_real_training_command(source_root="."),
    )

    policy = build_lambda_tiny_real_training_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.one_tiny_real_training_command is True
    assert policy.cpu_only is True
    assert policy.torch_required is False
    assert policy.gpu_required is False
    assert policy.no_network is True
    assert policy.no_dataset_or_model_download is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_tiny_real_training_policy_blocks_missing_safe_command(tmp_path):
    discovery_path = tmp_path / "blocked-discovery.json"
    write_lambda_tiny_real_training_command_discovery(
        discovery_path,
        LambdaTinyRealTrainingCommandDiscovery(
            discovery_status="no_safe_tiny_real_training_command_found",
            blockers=["local_tiny_real_training_smoke_failed"],
        ),
    )

    policy = build_lambda_tiny_real_training_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_tiny_real_training_command_found" in policy.blockers
