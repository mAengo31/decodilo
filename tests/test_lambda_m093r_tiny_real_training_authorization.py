from __future__ import annotations

from lambda_m092_helpers import write_m091_report, write_m092_chain

from decodilo.lambda_cloud.m093r_tiny_real_training_authorization import (
    build_lambda_m093r_tiny_real_training_authorization_from_paths,
)
from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    LambdaTinyRealTrainingCommandDiscovery,
    write_lambda_tiny_real_training_command_discovery,
)
from decodilo.lambda_cloud.tiny_real_training_policy import (
    build_lambda_tiny_real_training_policy_from_path,
    write_lambda_tiny_real_training_policy,
)
from decodilo.lambda_cloud.tiny_real_training_readiness import (
    build_lambda_tiny_real_training_readiness_from_path,
    write_lambda_tiny_real_training_readiness,
)


def test_m093r_tiny_real_training_authorization_is_future_only(tmp_path):
    paths = write_m092_chain(tmp_path)
    authorization = build_lambda_m093r_tiny_real_training_authorization_from_paths(
        readiness=paths["readiness"],
        command_discovery=paths["discovery"],
        policy=paths["policy"],
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m093r_tiny_real_training_smoke"
    )
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False
    assert authorization.torch_required is False
    assert authorization.gpu_required is False


def test_m093r_tiny_real_training_authorization_blocks_failed_discovery(tmp_path):
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_tiny_real_training_readiness(
        readiness_path,
        build_lambda_tiny_real_training_readiness_from_path(
            m091_report=write_m091_report(tmp_path),
        ),
    )
    write_lambda_tiny_real_training_command_discovery(
        discovery_path,
        LambdaTinyRealTrainingCommandDiscovery(
            discovery_status="no_safe_tiny_real_training_command_found",
            blockers=["local_tiny_real_training_smoke_failed"],
        ),
    )
    write_lambda_tiny_real_training_policy(
        policy_path,
        build_lambda_tiny_real_training_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    authorization = build_lambda_m093r_tiny_real_training_authorization_from_paths(
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert authorization.authorization_status == "not_authorized"
    assert "tiny_real_training_smoke_not_verified" in authorization.blockers
