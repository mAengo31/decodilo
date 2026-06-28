from __future__ import annotations

from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    LambdaTinyDecodiloSmokeDiscovery,
    write_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    build_lambda_tiny_decodilo_smoke_policy_from_path,
)


def test_tiny_smoke_policy_blocks_without_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_tiny_decodilo_smoke_discovery(
        discovery_path,
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )

    policy = build_lambda_tiny_decodilo_smoke_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_tiny_smoke_policy_passes_for_discovered_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_tiny_decodilo_smoke_discovery(
        discovery_path,
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="found_safe_tiny_smoke_command",
            argv_tokens=[
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
            ],
            timeout_seconds=30,
        ),
    )

    policy = build_lambda_tiny_decodilo_smoke_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.one_tiny_decodilo_smoke_command is True
    assert policy.bounded_timeout is True
    assert policy.bounded_output is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
