from lambda_m074_helpers import make_m073r2_workdir, write_m074_closeout_chain

from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    LambdaRuntimeProtocolSmokeDiscovery,
    write_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    build_lambda_runtime_protocol_smoke_policy_from_path,
    write_lambda_runtime_protocol_smoke_policy,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    build_lambda_runtime_protocol_smoke_readiness_from_path,
    write_lambda_runtime_protocol_smoke_readiness,
)


def test_m075r_authorization_not_authorized_without_runtime_command(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    paths = write_m074_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_runtime_protocol_smoke_readiness(
        readiness_path,
        build_lambda_runtime_protocol_smoke_readiness_from_path(
            tiny_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="no_safe_runtime_protocol_smoke_command_found",
            blockers=["no_safe_runtime_protocol_smoke_command_found"],
        ),
    )
    write_lambda_runtime_protocol_smoke_policy(
        policy_path,
        build_lambda_runtime_protocol_smoke_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    auth = build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths(
        tiny_smoke_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert auth.authorization_status == "not_authorized"
    assert "no_safe_runtime_protocol_smoke_command_found" in auth.blockers
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False


def test_m075r_authorization_future_only_when_runtime_command_exists(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    paths = write_m074_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_runtime_protocol_smoke_readiness(
        readiness_path,
        build_lambda_runtime_protocol_smoke_readiness_from_path(
            tiny_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="found_safe_runtime_protocol_smoke_command",
            command_category="dev_runtime_smoke_synthetic",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "runtime-smoke"],
            timeout_seconds=60,
        ),
    )
    write_lambda_runtime_protocol_smoke_policy(
        policy_path,
        build_lambda_runtime_protocol_smoke_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    auth = build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths(
        tiny_smoke_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert auth.authorization_status == (
        "authorized_for_future_m075r_runtime_protocol_smoke"
    )
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False
