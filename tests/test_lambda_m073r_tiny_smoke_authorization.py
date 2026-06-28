from __future__ import annotations

from decodilo.lambda_cloud.first_experiment_closeout import (
    LambdaFirstExperimentCloseout,
    write_lambda_first_experiment_closeout,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    build_lambda_m073r_tiny_smoke_authorization_from_paths,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    LambdaTinyDecodiloSmokeDiscovery,
    write_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    LambdaTinyDecodiloSmokePolicy,
    write_lambda_tiny_decodilo_smoke_policy,
)


def test_m073r_authorization_remains_not_authorized_without_command(tmp_path):
    closeout = tmp_path / "closeout.json"
    discovery = tmp_path / "discovery.json"
    policy = tmp_path / "policy.json"
    write_lambda_first_experiment_closeout(
        closeout,
        LambdaFirstExperimentCloseout(
            closeout_status="closed_success",
            closeout_succeeded=True,
            first_experiment_runtime_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            artifact_auditable=True,
            termination_verified=True,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_unapproved_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    write_lambda_tiny_decodilo_smoke_discovery(
        discovery,
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )
    write_lambda_tiny_decodilo_smoke_policy(
        policy,
        LambdaTinyDecodiloSmokePolicy(
            policy_status="blocked_no_safe_command",
            one_tiny_decodilo_smoke_command=False,
            bounded_timeout=False,
            bounded_output=False,
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )

    auth = build_lambda_m073r_tiny_smoke_authorization_from_paths(
        first_experiment_closeout=closeout,
        command_discovery=discovery,
        policy=policy,
    )

    assert auth.authorization_status == "not_authorized"
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False


def test_m073r_authorization_future_authorizes_discovered_command(tmp_path):
    closeout = tmp_path / "closeout.json"
    discovery = tmp_path / "discovery.json"
    policy = tmp_path / "policy.json"
    write_lambda_first_experiment_closeout(
        closeout,
        LambdaFirstExperimentCloseout(
            closeout_status="closed_success",
            closeout_succeeded=True,
            first_experiment_runtime_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            artifact_auditable=True,
            termination_verified=True,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_unapproved_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    write_lambda_tiny_decodilo_smoke_discovery(
        discovery,
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="found_safe_tiny_smoke_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "tiny-smoke"],
            timeout_seconds=30,
        ),
    )
    write_lambda_tiny_decodilo_smoke_policy(
        policy,
        LambdaTinyDecodiloSmokePolicy(
            policy_status="policy_passed",
            one_tiny_decodilo_smoke_command=True,
            bounded_timeout=True,
            bounded_output=True,
        ),
    )

    auth = build_lambda_m073r_tiny_smoke_authorization_from_paths(
        first_experiment_closeout=closeout,
        command_discovery=discovery,
        policy=policy,
    )

    assert auth.authorization_status == "authorized_for_future_m073r_tiny_decodilo_smoke"
    assert auth.run_now is False
    assert auth.launch_ready is False
    assert auth.launch_allowed is False
