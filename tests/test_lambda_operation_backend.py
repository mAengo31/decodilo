from __future__ import annotations

import subprocess
from pathlib import Path

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    LambdaL5DirectTcpRuntimeEvidencePackage,
    write_lambda_l5_restart_recovery_direct_tcp_evidence_package,
)
from decodilo.operation import OperationSpec, run_operation
from decodilo.operation.lambda_backend import LambdaOperationBackend, LambdaOperationBackendConfig


def test_lambda_operation_backend_blocks_by_default(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    backend = LambdaOperationBackend(command_runner=runner)
    result = run_operation(OperationSpec(name="blocked-l6"), workdir=tmp_path, backend=backend)

    assert result.backend == "lambda"
    assert result.status == "blocked"
    assert calls == []
    assert result.billable_action_performed is False
    assert result.remote_backend_enabled is False
    assert (
        result.backend_report["blocked_reason"]
        == "LambdaOperationBackend requires allow_billable_action=True"
    )
    assert (tmp_path / "lambda_l6_command_preview.json").exists()


def test_lambda_operation_backend_maps_l5_evidence_from_runner(tmp_path: Path) -> None:
    run_id = "lambda-l6-fake"
    evidence_root = tmp_path / "evidence"
    evidence_dir = evidence_root / run_id
    evidence_dir.mkdir(parents=True)
    package = LambdaL5DirectTcpRuntimeEvidencePackage(
        evidence_complete=True,
        lambda_l5_restart_recovery_direct_tcp_passed=True,
        run_id=run_id,
        remote_instance_count=3,
        remote_process_roles=["learner-0", "learner-1", "syncer"],
        distinct_role_instances=True,
        network_path="lambda_firewall_direct_tcp",
        firewall_rules_restored=True,
        direct_tcp_probe_passed=True,
        restart_attempted=True,
        restart_recovered=True,
        restart_round=24,
        rounds_after_restart=35,
        committed_sync_rounds=59,
        final_global_version=59,
        accepted_updates=118,
        useful_tokens_accepted=12390,
        inner_optimizer_semantics="adamw",
        outer_optimizer_semantics="nesterov",
        pseudo_gradient_numeric_check_passed=True,
        pseudo_gradient_numeric_rounds_checked=59,
        independent_nesterov_max_abs_error=0.0,
        checkpoint_outer_optimizer_step=59,
        checkpoint_velocity_max_abs_error=0.0,
        learner_artifacts_present=["learner-0", "learner-1"],
        final_instance_count=0,
        secret_scan_passed=True,
        blockers=[],
    )

    calls: list[list[str]] = []

    def runner(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        write_lambda_l5_restart_recovery_direct_tcp_evidence_package(
            evidence_dir / "lambda_l5_evidence_package.json",
            package,
        )
        return subprocess.CompletedProcess(command, 0, package.to_json(), "")

    backend = LambdaOperationBackend(
        config=LambdaOperationBackendConfig(
            allow_billable_action=True,
            run_id=run_id,
            evidence_root=evidence_root,
            env_file=tmp_path / ".env",
            ssh_key_name="test-key",
            ssh_private_key=tmp_path / "id_test",
        ),
        command_runner=runner,
    )

    result = run_operation(OperationSpec(name="l6-fake"), workdir=tmp_path, backend=backend)

    assert calls
    assert result.status == "completed"
    assert result.backend == "lambda"
    assert result.learners == 2
    assert result.remote_instance_count == 3
    assert result.remote_backend_enabled is True
    assert result.billable_action_performed is True
    assert result.network_path == "lambda_firewall_direct_tcp"
    assert result.firewall_rules_restored is True
    assert result.final_instance_count == 0
    assert result.syncer_recovered is True
    assert result.restart_round == 24
    assert result.rounds_after_restart == 35
    assert result.sync_rounds_committed == 59
    assert result.pseudo_gradient_numeric_check_passed is True
    assert result.pseudo_gradient_numeric_rounds_checked == 59
    assert result.backend_report["evidence_package_path"].endswith(
        "lambda_l5_evidence_package.json"
    )
