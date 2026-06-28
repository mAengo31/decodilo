from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.first_synthetic_experiment_discovery import (
    LambdaFirstSyntheticExperimentDiscovery,
    write_lambda_first_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.first_synthetic_experiment_policy import (
    build_lambda_first_synthetic_experiment_policy_from_path,
    write_lambda_first_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.first_synthetic_experiment_readiness import (
    build_lambda_first_synthetic_experiment_readiness_from_path,
    write_lambda_first_synthetic_experiment_readiness,
)
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    build_lambda_m077r_first_synthetic_experiment_authorization_from_paths,
)


def test_m077r_authorization_not_authorized_without_safe_command(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_first_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_first_synthetic_experiment_readiness_from_path(
            runtime_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_first_synthetic_experiment_discovery(
        discovery_path,
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            blockers=["no_safe_first_synthetic_experiment_command_found"],
        ),
    )
    write_lambda_first_synthetic_experiment_policy(
        policy_path,
        build_lambda_first_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m077r_first_synthetic_experiment_authorization_from_paths(
        runtime_smoke_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert authorization.authorization_status == "not_authorized"
    assert "no_safe_first_synthetic_experiment_command_found" in authorization.blockers
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_m077r_authorization_allows_future_when_safe_command_found(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_first_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_first_synthetic_experiment_readiness_from_path(
            runtime_smoke_closeout=paths["closeout"],
        ),
    )
    write_lambda_first_synthetic_experiment_discovery(
        discovery_path,
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="found_safe_first_synthetic_experiment_command",
            command_category="dev_synthetic_experiment_one_step",
            argv_tokens=[
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
            ],
            local_introspection_passed=True,
            timeout_seconds=120,
        ),
    )
    write_lambda_first_synthetic_experiment_policy(
        policy_path,
        build_lambda_first_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m077r_first_synthetic_experiment_authorization_from_paths(
        runtime_smoke_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m077r_first_synthetic_experiment"
    )
    assert authorization.command_category == "dev_synthetic_experiment_one_step"
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
