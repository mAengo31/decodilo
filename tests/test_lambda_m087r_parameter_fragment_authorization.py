from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir, write_m086_integrated_closeout_chain

from decodilo.lambda_cloud.m087r_parameter_fragment_authorization import (
    build_lambda_m087r_parameter_fragment_authorization_from_paths,
)
from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    LambdaParameterFragmentCommandDiscovery,
    write_lambda_parameter_fragment_command_discovery,
)
from decodilo.lambda_cloud.parameter_fragment_policy import (
    build_lambda_parameter_fragment_policy_from_path,
    write_lambda_parameter_fragment_policy,
)
from decodilo.lambda_cloud.parameter_fragment_readiness import (
    build_lambda_parameter_fragment_readiness_from_path,
    write_lambda_parameter_fragment_readiness,
)


def test_m087r_authorization_not_authorized_without_safe_command(tmp_path):
    closeout_paths = write_m086_integrated_closeout_chain(
        tmp_path,
        make_m085r_workdir(tmp_path),
    )
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_parameter_fragment_readiness(
        readiness_path,
        build_lambda_parameter_fragment_readiness_from_path(
            integrated_diloco_closeout=closeout_paths["closeout"],
        ),
    )
    write_lambda_parameter_fragment_command_discovery(
        discovery_path,
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            blockers=["no_safe_parameter_fragment_command_found"],
        ),
    )
    write_lambda_parameter_fragment_policy(
        policy_path,
        build_lambda_parameter_fragment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    report = build_lambda_m087r_parameter_fragment_authorization_from_paths(
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert report.authorization_status == "not_authorized"
    assert report.run_now is False
    assert "no_safe_parameter_fragment_command_found" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m087r_authorization_future_only_when_fragment_smoke_verified(tmp_path):
    closeout_paths = write_m086_integrated_closeout_chain(
        tmp_path,
        make_m085r_workdir(tmp_path),
    )
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_parameter_fragment_readiness(
        readiness_path,
        build_lambda_parameter_fragment_readiness_from_path(
            integrated_diloco_closeout=closeout_paths["closeout"],
        ),
    )
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
    write_lambda_parameter_fragment_policy(
        policy_path,
        build_lambda_parameter_fragment_policy_from_path(
            command_discovery=discovery_path,
        ),
    )

    report = build_lambda_m087r_parameter_fragment_authorization_from_paths(
        readiness=readiness_path,
        command_discovery=discovery_path,
        policy=policy_path,
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m087r_parameter_fragment_smoke"
    )
    assert report.expected_parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.run_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.blockers == []
