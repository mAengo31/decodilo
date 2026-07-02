"""Pathway-lite managed experiment planning for DiLoCo operations.

This module is intentionally narrow: it does not introduce a new scheduler or
runtime. It wraps the proven operation/Lambda planning surfaces with a named,
auditable managed-experiment plan for the next production-readiness step:
Lambda GPU causal-LM training with chunked/artifact transport.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from decodilo.operation.lambda_components import (
    LambdaOperationBackendConfig,
    LambdaOperationPlan,
    build_lambda_operation_plan,
)
from decodilo.operation.spec import OperationSpec

NEXT_CHUNKED_GPU_EXPERIMENT = "lambda_gpu_torch_causal_lm_chunked_transport"
PATHWAY_LITE_REQUIRED_EVIDENCE = [
    "remote_roles_syncer_and_two_learners",
    "actual_device_cuda",
    "inner_optimizer_adamw",
    "outer_optimizer_nesterov",
    "global_update_artifact_ref_present",
    "chunked_fragment_artifact_refs_present",
    "metadata_only_event_log",
    "pseudo_gradient_numeric_check_passed",
    "restart_recovered",
    "firewall_rules_restored",
    "final_instance_count_zero",
]


@dataclass(frozen=True)
class PathwayManagedExperimentPlan:
    """A fail-closed operation-layer plan for one managed experiment.

    It is a production-shaped wrapper around ``OperationSpec`` plus the Lambda
    plan; by default it is not launch-ready and not launch-allowed.
    """

    pathway_layer: str
    next_managed_experiment: str
    operation_spec: OperationSpec
    lambda_plan: LambdaOperationPlan
    required_evidence: list[str] = field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    production_scale_ready: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "pathway_layer": self.pathway_layer,
            "next_managed_experiment": self.next_managed_experiment,
            "operation_spec": self.operation_spec.model_dump(mode="json"),
            "lambda_plan": self.lambda_plan.to_preview_dict(),
            "required_evidence": list(self.required_evidence),
            "launch_ready": self.launch_ready,
            "launch_allowed": self.launch_allowed,
            "billable_action_performed": self.billable_action_performed,
            "production_scale_ready": self.production_scale_ready,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def build_next_lambda_gpu_chunked_experiment(
    *,
    name: str = "lambda-gpu-causal-lm-chunked-operation",
    learners: int = 2,
    steps: int = 16,
    min_quorum: int = 2,
    local_steps_per_sync: int = 1,
    fragments: int = 1,
    seed: int = 123,
    device: str = "cuda",
    vocab_size: int = 32,
    seq_len: int = 8,
    batch_size: int = 2,
    d_model: int = 16,
    num_layers: int = 1,
    num_heads: int = 2,
    learning_rate: float = 0.001,
    restart_syncer_after_round: int | None = 2,
    inline_payload_max_bytes: int = 1024,
    chunk_size_mb: int = 1,
) -> OperationSpec:
    """Return the next managed Pathway-lite experiment spec.

    The spec intentionally mirrors the proven tiny Lambda GPU causal-LM run but
    turns on chunked/artifact transport for payloads, checkpoints, merges, and
    global updates. This makes the next live experiment test the scale-facing
    transport path rather than re-testing inline JSONL transport.
    """

    return OperationSpec.torch_causal_lm_profile(
        name=name,
        learners=learners,
        steps=steps,
        min_quorum=min_quorum,
        local_steps_per_sync=local_steps_per_sync,
        fragments=fragments,
        seed=seed,
        device=device,
        vocab_size=vocab_size,
        seq_len=seq_len,
        batch_size=batch_size,
        d_model=d_model,
        num_layers=num_layers,
        num_heads=num_heads,
        learning_rate=learning_rate,
        restart_syncer_after_round=restart_syncer_after_round,
        payload_storage_mode="chunked",
        checkpoint_storage_mode="chunked",
        merge_mode="streaming_chunked",
        global_update_storage_mode="chunked",
        inline_payload_max_bytes=inline_payload_max_bytes,
        chunk_size_mb=chunk_size_mb,
    )


def compile_pathway_managed_experiment(
    spec: OperationSpec,
    *,
    workdir: Path,
    lambda_config: LambdaOperationBackendConfig | None = None,
) -> PathwayManagedExperimentPlan:
    """Compile an operation spec into the Pathway-lite Lambda plan.

    This is a no-live compile step. The returned plan remains fail-closed;
    execution still requires a separately armed backend.
    """

    config = lambda_config or LambdaOperationBackendConfig()
    lambda_plan = build_lambda_operation_plan(spec, config=config, workdir=workdir)
    return PathwayManagedExperimentPlan(
        pathway_layer="pathway_lite",
        next_managed_experiment=NEXT_CHUNKED_GPU_EXPERIMENT,
        operation_spec=spec,
        lambda_plan=lambda_plan,
        required_evidence=list(PATHWAY_LITE_REQUIRED_EVIDENCE),
    )

SIX_STEP_PRODUCTION_CANDIDATE = "lambda_gpu_six_step_production_candidate"
SIX_STEP_REQUIRED_EVIDENCE = PATHWAY_LITE_REQUIRED_EVIDENCE + [
    "larger_model_above_13k_parameters",
    "artifact_transfer_mode_object_store",
    "artifact_storage_backend_syncer_object_store",
    "four_learner_local_profile",
    "failure_matrix_profile",
    "external_durable_backend_not_claimed",
    "production_scale_ready_false",
]


def build_six_step_production_candidate_experiments(
    *,
    seed: int = 123,
    device: str = "cuda",
) -> dict[str, OperationSpec]:
    """Return fail-closed managed profiles for the six production-readiness steps.

    These profiles intentionally advance scale pressure while preserving honest
    boundaries: they are production-shaped candidates, not production-scale
    readiness claims. The live profile remains bounded; larger/more-learner and
    failure profiles are intended for local verification first.
    """

    common = {
        "seed": seed,
        "device": device,
        "payload_storage_mode": "chunked",
        "checkpoint_storage_mode": "chunked",
        "merge_mode": "streaming_chunked",
        "global_update_storage_mode": "chunked",
        "inline_payload_max_bytes": 1024,
        "chunk_size_mb": 1,
        "artifact_transfer_mode": "object_store",
    }
    return {
        "larger_model": OperationSpec.torch_causal_lm_profile(
            name="six-step-larger-model-object-store",
            learners=2,
            steps=12,
            min_quorum=2,
            local_steps_per_sync=1,
            vocab_size=96,
            seq_len=24,
            batch_size=2,
            d_model=48,
            num_layers=1,
            num_heads=4,
            restart_syncer_after_round=2,
            production_step_tags=["larger_model", "artifact_pressure", "object_store"],
            **common,
        ),
        "more_learners": OperationSpec.torch_causal_lm_profile(
            name="six-step-four-learner-object-store",
            learners=4,
            steps=20,
            min_quorum=3,
            local_steps_per_sync=5,
            vocab_size=64,
            seq_len=16,
            batch_size=2,
            d_model=32,
            num_layers=1,
            num_heads=4,
            production_step_tags=["more_learners", "object_store"],
            **common,
        ),
        "failure_matrix": OperationSpec.torch_causal_lm_profile(
            name="six-step-failure-matrix-object-store",
            learners=3,
            steps=20,
            min_quorum=2,
            local_steps_per_sync=5,
            vocab_size=64,
            seq_len=16,
            batch_size=2,
            d_model=32,
            num_layers=1,
            num_heads=4,
            restart_syncer_after_round=2,
            production_step_tags=["failure_matrix", "syncer_restart", "slow_learner"],
            **common,
        ),
    }


def compile_six_step_production_candidate(
    *,
    workdir: Path,
    lambda_config: LambdaOperationBackendConfig | None = None,
) -> dict[str, PathwayManagedExperimentPlan]:
    """Compile all six-step candidate profiles into fail-closed Lambda plans."""

    config = lambda_config or LambdaOperationBackendConfig()
    return {
        name: PathwayManagedExperimentPlan(
            pathway_layer="pathway_lite_six_step_candidate",
            next_managed_experiment=SIX_STEP_PRODUCTION_CANDIDATE,
            operation_spec=spec,
            lambda_plan=build_lambda_operation_plan(spec, config=config, workdir=workdir),
            required_evidence=list(SIX_STEP_REQUIRED_EVIDENCE),
        )
        for name, spec in build_six_step_production_candidate_experiments().items()
    }
