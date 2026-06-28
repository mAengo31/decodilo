"""Backend-owned Lambda operation planning and evidence mapping components."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    LambdaL5DirectTcpRuntimeEvidencePackage,
)
from decodilo.operation.result import OperationResult
from decodilo.operation.spec import OperationSafetyEnvelope, OperationSpec


@dataclass(frozen=True)
class LambdaOperationBackendConfig:
    """Configuration for the real Lambda operation backend wrapper.

    ``allow_billable_action`` is false by default. Setting it true authorizes
    invoking the L5 runner, which launches real Lambda instances. Tests should
    inject a fake command runner and fake evidence.
    """

    allow_billable_action: bool = False
    run_id: str | None = None
    env_file: Path = Path(".env")
    ssh_private_key: Path = Path.home() / ".ssh" / "diloco_lambda"
    ssh_key_name: str | None = None
    region: str = "us-east-1"
    instance_type: str = "gpu_1x_a10"
    port: int = 28080
    restart_after_round: int = 20
    evidence_root: Path | None = None
    runner_script: Path = Path("tools/lambda_l5_runner.py")


@dataclass(frozen=True)
class LambdaOperationPlan:
    """Executable Lambda operation plan produced from an OperationSpec."""

    backend: str
    operation_name: str
    run_id: str
    evidence_root: Path
    evidence_package_path: Path
    command: list[str]
    redacted_command: list[str]
    remote_roles: list[str]
    network_path: str
    restart_strategy: str
    restart_after_round: int
    trainer_type: str
    trainer_config_json: str
    vector_dim: int
    learners: int
    steps: int
    min_quorum: int
    local_steps_per_sync: int
    fragments: int
    real_model_training_claimed: bool
    paper_scale_training_claimed: bool
    payload_storage_mode: str
    checkpoint_storage_mode: str
    merge_mode: str
    global_update_storage_mode: str
    inline_payload_max_bytes: int
    chunk_size_bytes: int
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_preview_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "operation_name": self.operation_name,
            "run_id": self.run_id,
            "evidence_root": str(self.evidence_root),
            "evidence_package_path": str(self.evidence_package_path),
            "command": self.redacted_command,
            "remote_roles": self.remote_roles,
            "network_path": self.network_path,
            "restart_strategy": self.restart_strategy,
            "restart_after_round": self.restart_after_round,
            "trainer_type": self.trainer_type,
            "trainer_config_json": self.trainer_config_json,
            "vector_dim": self.vector_dim,
            "learners": self.learners,
            "steps": self.steps,
            "min_quorum": self.min_quorum,
            "local_steps_per_sync": self.local_steps_per_sync,
            "fragments": self.fragments,
            "real_model_training_claimed": self.real_model_training_claimed,
            "paper_scale_training_claimed": self.paper_scale_training_claimed,
            "payload_storage_mode": self.payload_storage_mode,
            "checkpoint_storage_mode": self.checkpoint_storage_mode,
            "merge_mode": self.merge_mode,
            "global_update_storage_mode": self.global_update_storage_mode,
            "inline_payload_max_bytes": self.inline_payload_max_bytes,
            "chunk_size_bytes": self.chunk_size_bytes,
            "launch_ready": self.launch_ready,
            "launch_allowed": self.launch_allowed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_preview_dict(), indent=2, sort_keys=True) + "\n"


def build_lambda_operation_plan(
    spec: OperationSpec,
    *,
    config: LambdaOperationBackendConfig,
    workdir: Path,
) -> LambdaOperationPlan:
    run_id = config.run_id or f"lambda-l6-{spec.name}"
    evidence_root = config.evidence_root or (workdir / "lambda_l6_evidence")
    evidence_package_path = evidence_root / run_id / "lambda_l5_evidence_package.json"
    trainer_config_json = json.dumps(spec.trainer_config, sort_keys=True)
    command = build_lambda_l5_runner_command(
        config=config,
        spec=spec,
        run_id=run_id,
        evidence_root=evidence_root,
        trainer_config_json=trainer_config_json,
    )
    return LambdaOperationPlan(
        backend="lambda",
        operation_name=spec.name,
        run_id=run_id,
        evidence_root=evidence_root,
        evidence_package_path=evidence_package_path,
        command=command,
        redacted_command=redact_lambda_command(command),
        remote_roles=["syncer", "learner-0", "learner-1"],
        network_path="lambda_firewall_direct_tcp",
        restart_strategy="syncer_checkpoint_restart",
        restart_after_round=config.restart_after_round,
        trainer_type=spec.trainer_type,
        trainer_config_json=trainer_config_json,
        vector_dim=spec.vector_dim,
        learners=spec.learners,
        steps=spec.steps,
        min_quorum=spec.min_quorum,
        local_steps_per_sync=spec.local_steps_per_sync,
        fragments=spec.fragments,
        real_model_training_claimed=bool(
            spec.trainer_config.get("real_model_training_claimed", False)
        ),
        paper_scale_training_claimed=bool(
            spec.trainer_config.get("paper_scale_training_claimed", False)
        ),
        payload_storage_mode=spec.payload_storage_mode,
        checkpoint_storage_mode=spec.checkpoint_storage_mode,
        merge_mode=spec.merge_mode,
        global_update_storage_mode=spec.global_update_storage_mode,
        inline_payload_max_bytes=spec.inline_payload_max_bytes,
        chunk_size_bytes=spec.chunk_size_bytes,
    )


def build_lambda_l5_runner_command(
    *,
    config: LambdaOperationBackendConfig,
    spec: OperationSpec,
    run_id: str,
    evidence_root: Path,
    trainer_config_json: str,
) -> list[str]:
    command = [
        sys.executable,
        str(config.runner_script),
        "--env-file",
        str(config.env_file),
        "--ssh-private-key",
        str(config.ssh_private_key),
        "--region",
        config.region,
        "--instance-type",
        config.instance_type,
        "--port",
        str(config.port),
        "--run-id",
        run_id,
        "--evidence-root",
        str(evidence_root),
        "--restart-after-round",
        str(config.restart_after_round),
        "--trainer-type",
        spec.trainer_type,
        "--trainer-config-json",
        trainer_config_json,
        "--vector-dim",
        str(spec.vector_dim),
        "--learners",
        str(spec.learners),
        "--steps",
        str(spec.steps),
        "--min-quorum",
        str(spec.min_quorum),
        "--local-steps-per-sync",
        str(spec.local_steps_per_sync),
        "--fragments",
        str(spec.fragments),
        "--payload-storage-mode",
        spec.payload_storage_mode,
        "--checkpoint-storage-mode",
        spec.checkpoint_storage_mode,
        "--merge-mode",
        spec.merge_mode,
        "--global-update-storage-mode",
        spec.global_update_storage_mode,
        "--inline-payload-max-bytes",
        str(spec.inline_payload_max_bytes),
        "--chunk-size-mb",
        str(max(1, spec.chunk_size_bytes // (1024 * 1024))),
    ]
    if config.ssh_key_name:
        command.extend(["--ssh-key-name", config.ssh_key_name])
    return command


def redact_lambda_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for item in command:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        redacted.append(item)
        if item in {"--ssh-private-key"}:
            redact_next = True
    return redacted


def lambda_operation_result_from_l5_package(
    *,
    spec: OperationSpec,
    package: LambdaL5DirectTcpRuntimeEvidencePackage,
    plan: LambdaOperationPlan,
    completed: subprocess.CompletedProcess[str],
) -> OperationResult:
    return OperationResult(
        operation_name=spec.name,
        backend="lambda",
        status="completed" if package.lambda_l5_restart_recovery_direct_tcp_passed else "failed",
        inner_optimizer_semantics=package.inner_optimizer_semantics,
        outer_optimizer_semantics=package.outer_optimizer_semantics,
        outer_momentum=spec.outer_momentum,
        learners=len(
            [role for role in package.remote_process_roles if role.startswith("learner-")]
        ),
        final_global_version=package.final_global_version,
        sync_rounds_committed=package.committed_sync_rounds,
        training_attempted=package.committed_sync_rounds > 0,
        real_training_mechanics_exercised=True,
        optimizer_state_present=package.checkpoint_outer_optimizer_step is not None,
        nesterov_outer_optimizer_exercised=package.outer_optimizer_semantics == "nesterov",
        outer_optimizer_semantics_checked=package.outer_optimizer_semantics == spec.outer_optimizer,
        pseudo_gradient_numeric_check_passed=package.pseudo_gradient_numeric_check_passed,
        pseudo_gradient_numeric_rounds_checked=package.pseudo_gradient_numeric_rounds_checked,
        pseudo_gradient_check_passed=package.pseudo_gradient_numeric_check_passed,
        replay_passed=package.pseudo_gradient_numeric_check_passed,
        metric_validation_passed=package.evidence_complete,
        syncer_recovered=package.restart_recovered,
        remote_backend_enabled=True,
        billable_action_performed=package.billable_action_performed,
        remote_instance_count=package.remote_instance_count,
        network_path=package.network_path,
        direct_tcp_probe_passed=package.direct_tcp_probe_passed,
        firewall_rules_restored=package.firewall_rules_restored,
        final_instance_count=package.final_instance_count,
        restart_round=package.restart_round,
        rounds_after_restart=package.rounds_after_restart,
        safety=OperationSafetyEnvelope(network_scope="none"),
        backend_report={
            "evidence_package_path": str(plan.evidence_package_path),
            "run_id": package.run_id,
            "command": plan.redacted_command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:] if completed.stdout else "",
            "stderr_tail": completed.stderr[-4000:] if completed.stderr else "",
            "blockers": package.blockers,
        },
    )
