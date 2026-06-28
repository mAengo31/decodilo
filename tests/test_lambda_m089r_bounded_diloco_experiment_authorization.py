from __future__ import annotations

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    LambdaBoundedDilocoExperimentCommandDiscovery,
    write_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    build_lambda_bounded_diloco_experiment_policy_from_path,
    write_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    LambdaBoundedDilocoExperimentReadiness,
    write_lambda_bounded_diloco_experiment_readiness,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths,
)


def test_m089r_authorization_not_authorized_without_bounded_command(tmp_path):
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_bounded_diloco_experiment_readiness(
        readiness_path,
        LambdaBoundedDilocoExperimentReadiness(
            readiness_status=(
                "ready_for_first_bounded_synthetic_diloco_experiment_planning"
            ),
            cloud_lifecycle_ready=True,
            remote_source_dependency_path_ready=True,
            learner_syncer_protocol_ready=True,
            adamw_nesterov_optimizer_semantics_ready=True,
            integrated_protocol_optimizer_ready=True,
            synthetic_parameter_fragment_semantics_ready=True,
        ),
    )
    write_lambda_bounded_diloco_experiment_command_discovery(
        discovery_path,
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="no_safe_bounded_diloco_experiment_command_found",
            blockers=["no_safe_bounded_diloco_experiment_command_found"],
        ),
    )
    write_lambda_bounded_diloco_experiment_policy(
        policy_path,
        build_lambda_bounded_diloco_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    report = build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths(
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert report.authorization_status == "not_authorized"
    assert "no_safe_bounded_diloco_experiment_command_found" in report.blockers
    assert report.run_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m089r_authorization_future_authorized_with_safe_bounded_command(tmp_path):
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_bounded_diloco_experiment_readiness(
        readiness_path,
        LambdaBoundedDilocoExperimentReadiness(
            readiness_status=(
                "ready_for_first_bounded_synthetic_diloco_experiment_planning"
            ),
            cloud_lifecycle_ready=True,
            remote_source_dependency_path_ready=True,
            learner_syncer_protocol_ready=True,
            adamw_nesterov_optimizer_semantics_ready=True,
            integrated_protocol_optimizer_ready=True,
            synthetic_parameter_fragment_semantics_ready=True,
        ),
    )
    write_lambda_bounded_diloco_experiment_command_discovery(
        discovery_path,
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="found_safe_bounded_diloco_experiment_command",
            command_category="dev_bounded_diloco_experiment_one_step",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "bounded-diloco-experiment",
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-bounded-diloco-experiment.json",
            ],
            timeout_seconds=180,
        ),
    )
    write_lambda_bounded_diloco_experiment_policy(
        policy_path,
        build_lambda_bounded_diloco_experiment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    report = build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths(
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m089r_bounded_diloco_experiment"
    )
    assert report.command_category == "dev_bounded_diloco_experiment_one_step"
    assert report.blockers == []
    assert report.run_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
