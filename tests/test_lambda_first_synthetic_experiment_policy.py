from __future__ import annotations

from decodilo.lambda_cloud.first_synthetic_experiment_discovery import (
    LambdaFirstSyntheticExperimentDiscovery,
    write_lambda_first_synthetic_experiment_discovery,
)
from decodilo.lambda_cloud.first_synthetic_experiment_policy import (
    build_lambda_first_synthetic_experiment_policy_from_path,
)


def test_first_synthetic_experiment_policy_blocks_when_no_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_first_synthetic_experiment_discovery(
        discovery_path,
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            blockers=["no_safe_first_synthetic_experiment_command_found"],
        ),
    )

    policy = build_lambda_first_synthetic_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_first_synthetic_experiment_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_first_synthetic_experiment_policy_passes_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
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
            generated_workdir_path="/tmp/decodilo-synthetic-experiment",
        ),
    )

    policy = build_lambda_first_synthetic_experiment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.one_bounded_synthetic_experiment_command is True
    assert policy.bounded_timeout is True
    assert policy.bounded_output is True
    assert policy.synthetic_only is True
    assert policy.no_internet is True
    assert policy.no_model_or_data_download is True
    assert policy.no_package_install_beyond_local_wheelhouse is True
    assert policy.no_real_training is True
    assert policy.no_background_process is True
    assert policy.halt_after_first_failed_live_stage is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
