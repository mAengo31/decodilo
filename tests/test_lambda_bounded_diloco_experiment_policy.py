from __future__ import annotations

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    LambdaBoundedDilocoExperimentCommandDiscovery,
    write_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    build_lambda_bounded_diloco_experiment_policy_from_path,
    write_lambda_bounded_diloco_experiment_policy,
)


def test_bounded_diloco_policy_blocks_missing_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_bounded_diloco_experiment_command_discovery(
        discovery_path,
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="no_safe_bounded_diloco_experiment_command_found",
            blockers=["no_safe_bounded_diloco_experiment_command_found"],
            recommendation="python -m decodilo.cli dev bounded-diloco-experiment",
        ),
    )

    report = build_lambda_bounded_diloco_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert report.policy_status == "blocked_no_safe_command"
    assert "no_safe_bounded_diloco_experiment_command_found" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_bounded_diloco_policy_accepts_safe_future_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
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
            ],
            timeout_seconds=180,
        ),
    )

    report = build_lambda_bounded_diloco_experiment_policy_from_path(
        command_discovery=discovery_path,
    )
    write_lambda_bounded_diloco_experiment_policy(policy_path, report)

    assert report.policy_status == "policy_passed"
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.fragments == 2
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.launch_ready is False
    assert report.launch_allowed is False
