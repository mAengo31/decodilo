from __future__ import annotations

from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    LambdaParameterFragmentCommandDiscovery,
    write_lambda_parameter_fragment_command_discovery,
)
from decodilo.lambda_cloud.parameter_fragment_policy import (
    build_lambda_parameter_fragment_policy_from_path,
)


def test_parameter_fragment_policy_blocks_when_no_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_parameter_fragment_command_discovery(
        discovery_path,
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            blockers=["no_safe_parameter_fragment_command_found"],
        ),
    )

    policy = build_lambda_parameter_fragment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "no_safe_parameter_fragment_command_found" in policy.blockers
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_parameter_fragment_policy_passes_for_verified_synthetic_fragments(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_parameter_fragment_command_discovery(
        discovery_path,
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="found_safe_parameter_fragment_command",
            command_category="dev_parameter_fragment_smoke_two_fragments_one_step",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "parameter-fragment-smoke",
                "--synthetic",
                "--fragments",
                "2",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-parameter-fragment-smoke.json",
            ],
            timeout_seconds=120,
            expected_parameter_fragment_semantics="synthetic_vector_fragments",
        ),
    )

    policy = build_lambda_parameter_fragment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "policy_passed"
    assert policy.expected_parameter_fragment_semantics == "synthetic_vector_fragments"
    assert policy.one_bounded_parameter_fragment_command is True
    assert policy.fragments == 2
    assert policy.max_steps == 1
    assert policy.no_real_training is True
    assert policy.no_background_process is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_parameter_fragment_policy_blocks_unverified_fragment_semantics(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_parameter_fragment_command_discovery(
        discovery_path,
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            blockers=["parameter_fragment_smoke_not_verified"],
            expected_parameter_fragment_semantics="storage_chunk_only",
        ),
    )

    policy = build_lambda_parameter_fragment_policy_from_path(
        command_discovery=discovery_path,
    )

    assert policy.policy_status == "blocked_no_safe_command"
    assert "parameter_fragment_smoke_not_verified" in policy.blockers
