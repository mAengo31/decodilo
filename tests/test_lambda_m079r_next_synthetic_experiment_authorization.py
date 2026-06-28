from __future__ import annotations

from lambda_m078_helpers import (
    make_m077r_workdir,
    safe_next_discovery_kwargs,
    write_m078_closeout_chain,
)

from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    build_lambda_m079r_next_synthetic_experiment_authorization_from_paths,
)
from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    LambdaNextSyntheticExperimentDiscovery,
    write_lambda_next_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.next_synthetic_experiment_policy import (
    build_lambda_next_synthetic_experiment_policy_from_path,
    write_lambda_next_synthetic_experiment_policy,
)
from decodilo.lambda_cloud.next_synthetic_experiment_readiness import (
    build_lambda_next_synthetic_experiment_readiness_from_path,
    write_lambda_next_synthetic_experiment_readiness,
)


def test_m079r_authorization_not_authorized_without_safe_command(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_next_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_next_synthetic_experiment_readiness_from_path(
            synthetic_experiment_closeout=paths["closeout"],
        ),
    )
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            blockers=["no_safe_next_synthetic_experiment_command_found"],
        ),
    )
    write_lambda_next_synthetic_experiment_policy(
        policy_path,
        build_lambda_next_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m079r_next_synthetic_experiment_authorization_from_paths(
        synthetic_experiment_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert authorization.authorization_status == "not_authorized"
    assert "no_safe_next_synthetic_experiment_command_found" in authorization.blockers
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_m079r_authorization_allows_future_when_safe_command_found(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_next_synthetic_experiment_readiness(
        readiness_path,
        build_lambda_next_synthetic_experiment_readiness_from_path(
            synthetic_experiment_closeout=paths["closeout"],
        ),
    )
    write_lambda_next_synthetic_experiment_discovery(
        discovery_path,
        LambdaNextSyntheticExperimentDiscovery(**safe_next_discovery_kwargs()),
    )
    write_lambda_next_synthetic_experiment_policy(
        policy_path,
        build_lambda_next_synthetic_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m079r_next_synthetic_experiment_authorization_from_paths(
        synthetic_experiment_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m079r_next_synthetic_experiment"
    )
    assert authorization.command_category == "dev_learner_syncer_smoke_one_step"
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
