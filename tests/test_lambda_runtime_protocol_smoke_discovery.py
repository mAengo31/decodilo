import pytest

from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    LambdaRuntimeProtocolSmokeDiscovery,
    discover_lambda_runtime_protocol_smoke_command,
)


def test_runtime_protocol_smoke_discovery_finds_safe_runtime_command():
    discovery = discover_lambda_runtime_protocol_smoke_command(source_root=".")

    assert discovery.discovery_status == "found_safe_runtime_protocol_smoke_command"
    assert discovery.local_introspection_passed is True
    assert discovery.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "runtime-smoke",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-runtime-smoke.json",
    ]
    assert discovery.no_external_network is True
    assert discovery.no_real_training is True
    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False


def test_runtime_protocol_smoke_discovery_can_represent_safe_command():
    discovery = LambdaRuntimeProtocolSmokeDiscovery(
        discovery_status="found_safe_runtime_protocol_smoke_command",
        command_category="dev_runtime_smoke_synthetic",
        argv_tokens=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "runtime-smoke",
            "--synthetic",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-runtime-smoke.json",
        ],
        local_introspection_passed=True,
        timeout_seconds=60,
        generated_workdir_path="/tmp/decodilo-runtime-smoke",
    )

    assert discovery.discovery_status == "found_safe_runtime_protocol_smoke_command"
    assert discovery.no_real_training is True
    assert discovery.no_downloads is True
    assert discovery.gpu_required is False


def test_runtime_protocol_smoke_discovery_rejects_unsafe_found_command():
    with pytest.raises(ValueError, match="unsafe flags"):
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="found_safe_runtime_protocol_smoke_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "runtime-smoke"],
            timeout_seconds=60,
            no_external_network=False,
        )
