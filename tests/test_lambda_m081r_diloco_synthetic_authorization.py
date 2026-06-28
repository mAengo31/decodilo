from __future__ import annotations

from lambda_m080_helpers import (
    make_m079r2_workdir,
    safe_diloco_discovery_kwargs,
    write_m080_closeout_chain,
)

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    LambdaDilocoSyntheticCommandDiscovery,
    write_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    build_lambda_diloco_synthetic_policy_from_path,
    write_lambda_diloco_synthetic_policy,
)
from decodilo.lambda_cloud.diloco_synthetic_readiness import (
    build_lambda_diloco_synthetic_readiness_from_path,
    write_lambda_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    build_lambda_m081r_diloco_synthetic_authorization_from_paths,
)


def test_m081r_authorization_not_authorized_without_diloco_command(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_diloco_synthetic_readiness(
        readiness_path,
        build_lambda_diloco_synthetic_readiness_from_path(
            learner_syncer_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="no_safe_diloco_synthetic_command_found",
            blockers=["no_safe_diloco_synthetic_command_found"],
        ),
    )
    write_lambda_diloco_synthetic_policy(
        policy_path,
        build_lambda_diloco_synthetic_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m081r_diloco_synthetic_authorization_from_paths(
        learner_syncer_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert authorization.authorization_status == "not_authorized"
    assert "no_safe_diloco_synthetic_command_found" in authorization.blockers
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_m081r_authorization_allows_future_when_diloco_command_is_safe(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_diloco_synthetic_readiness(
        readiness_path,
        build_lambda_diloco_synthetic_readiness_from_path(
            learner_syncer_closeout=paths["closeout"],
        ),
    )
    write_lambda_diloco_synthetic_command_discovery(
        discovery_path,
        LambdaDilocoSyntheticCommandDiscovery(**safe_diloco_discovery_kwargs()),
    )
    write_lambda_diloco_synthetic_policy(
        policy_path,
        build_lambda_diloco_synthetic_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m081r_diloco_synthetic_authorization_from_paths(
        learner_syncer_closeout=paths["closeout"],
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m081r_diloco_synthetic_experiment"
    )
    assert authorization.blockers == []
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
