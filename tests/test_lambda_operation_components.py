from __future__ import annotations

import subprocess
from pathlib import Path

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    LambdaL5DirectTcpRuntimeEvidencePackage,
)
from decodilo.operation.lambda_components import (
    LambdaOperationBackendConfig,
    build_lambda_operation_plan,
    lambda_operation_result_from_l5_package,
)
from decodilo.operation.spec import OperationSpec


def _fake_l5_package() -> LambdaL5DirectTcpRuntimeEvidencePackage:
    return LambdaL5DirectTcpRuntimeEvidencePackage(
        evidence_complete=True,
        lambda_l5_restart_recovery_direct_tcp_passed=True,
        run_id="lambda-l6-components",
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


def test_lambda_operation_plan_is_backend_owned_and_redacted(tmp_path: Path) -> None:
    config = LambdaOperationBackendConfig(
        run_id="lambda-l6-plan",
        evidence_root=tmp_path / "evidence",
        env_file=tmp_path / ".env",
        ssh_key_name="test-key",
        ssh_private_key=tmp_path / "private-key.pem",
        restart_after_round=20,
    )

    plan = build_lambda_operation_plan(
        OperationSpec(name="l6-plan"),
        config=config,
        workdir=tmp_path,
    )

    assert plan.backend == "lambda"
    assert plan.run_id == "lambda-l6-plan"
    assert plan.remote_roles == ["syncer", "learner-0", "learner-1"]
    assert plan.network_path == "lambda_firewall_direct_tcp"
    assert plan.restart_strategy == "syncer_checkpoint_restart"
    assert plan.evidence_package_path == (
        tmp_path / "evidence" / "lambda-l6-plan" / "lambda_l5_evidence_package.json"
    )
    assert "--restart-after-round" in plan.command
    assert "20" in plan.command
    assert str(tmp_path / "private-key.pem") in plan.command
    assert str(tmp_path / "private-key.pem") not in plan.redacted_command
    assert "<redacted>" in plan.redacted_command
    assert plan.launch_ready is False
    assert plan.launch_allowed is False


def test_lambda_operation_result_mapping_uses_l5_evidence(tmp_path: Path) -> None:
    spec = OperationSpec(name="l6-map")
    config = LambdaOperationBackendConfig(run_id="lambda-l6-components")
    plan = build_lambda_operation_plan(spec, config=config, workdir=tmp_path)
    completed = subprocess.CompletedProcess(plan.command, 0, "stdout", "stderr")

    result = lambda_operation_result_from_l5_package(
        spec=spec,
        package=_fake_l5_package(),
        plan=plan,
        completed=completed,
    )

    assert result.status == "completed"
    assert result.backend == "lambda"
    assert result.remote_backend_enabled is True
    assert result.billable_action_performed is True
    assert result.remote_instance_count == 3
    assert result.network_path == "lambda_firewall_direct_tcp"
    assert result.firewall_rules_restored is True
    assert result.final_instance_count == 0
    assert result.syncer_recovered is True
    assert result.restart_round == 24
    assert result.rounds_after_restart == 35
    assert result.sync_rounds_committed == 59
    assert result.backend_report["evidence_package_path"] == str(plan.evidence_package_path)



def test_lambda_operation_plan_carries_torch_causal_lm_trainer_config(tmp_path: Path) -> None:
    spec = OperationSpec.torch_causal_lm_profile(
        name="lambda-gpu-profile",
        learners=2,
        min_quorum=2,
        steps=8,
        device="cuda",
        vocab_size=32,
        seq_len=8,
        batch_size=2,
        d_model=16,
        num_layers=1,
        num_heads=2,
        learning_rate=0.001,
    )
    config = LambdaOperationBackendConfig(
        run_id="lambda-l6-gpu-profile",
        evidence_root=tmp_path / "evidence",
        env_file=tmp_path / ".env",
        ssh_key_name="test-key",
        ssh_private_key=tmp_path / "private-key.pem",
        restart_after_round=4,
    )

    plan = build_lambda_operation_plan(spec, config=config, workdir=tmp_path)

    command = plan.command
    assert "--trainer-type" in command
    assert command[command.index("--trainer-type") + 1] == "torch_causal_lm"
    assert "--trainer-config-json" in command
    trainer_config_json = command[command.index("--trainer-config-json") + 1]
    assert '"device": "cuda"' in trainer_config_json
    assert '"optimizer": "adamw"' in trainer_config_json
    assert "--vector-dim" in command
    assert command[command.index("--vector-dim") + 1] == str(spec.vector_dim)
    assert "--learners" in command
    assert command[command.index("--learners") + 1] == "2"
    assert "--steps" in command
    assert command[command.index("--steps") + 1] == "8"
    preview = plan.to_preview_dict()
    assert preview["trainer_type"] == "torch_causal_lm"
    assert preview["real_model_training_claimed"] is True
    assert preview["paper_scale_training_claimed"] is False
