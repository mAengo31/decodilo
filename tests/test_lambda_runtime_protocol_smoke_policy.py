from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    LambdaRuntimeProtocolSmokeDiscovery,
    write_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    build_lambda_runtime_protocol_smoke_policy_from_path,
)


def test_runtime_protocol_smoke_policy_blocks_without_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="no_safe_runtime_protocol_smoke_command_found",
            blockers=["no_safe_runtime_protocol_smoke_command_found"],
        ),
    )

    policy = build_lambda_runtime_protocol_smoke_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert policy.one_runtime_protocol_smoke_command is False
    assert "no_safe_runtime_protocol_smoke_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_runtime_protocol_smoke_policy_accepts_safe_synthetic_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="found_safe_runtime_protocol_smoke_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "runtime-smoke"],
            timeout_seconds=60,
        ),
    )

    policy = build_lambda_runtime_protocol_smoke_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.synthetic_only is True
    assert policy.no_internet is True
    assert policy.no_long_training is True


def test_runtime_protocol_smoke_policy_rejects_missing_timeout(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="found_safe_runtime_protocol_smoke_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "runtime-smoke"],
        ),
    )

    policy = build_lambda_runtime_protocol_smoke_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "runtime_protocol_smoke_timeout_missing" in policy.blockers
