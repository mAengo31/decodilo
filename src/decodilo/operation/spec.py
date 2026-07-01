"""Declarative operation spec and safety envelope for the pathway layer."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.chunked_payloads import chunk_size_bytes_from_mb
from decodilo.runtime.chunked_runtime_modes import validate_runtime_modes


class OperationSafetyEnvelope(BaseModel):
    """Explicit, fail-closed safety envelope carried by every operation.

    The defaults encode the project invariant: nothing here may launch remote
    compute, perform billable actions, or claim real/paper-scale training.
    """

    model_config = ConfigDict(frozen=True)

    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    remote_backend_enabled: bool = False
    real_model_training_claimed: bool = False
    paper_scale_training_claimed: bool = False
    network_scope: str = "localhost_only"

    @model_validator(mode="after")
    def _fail_closed(self) -> OperationSafetyEnvelope:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("operation safety envelope cannot enable launch or billing")
        if self.real_model_training_claimed or self.paper_scale_training_claimed:
            raise ValueError("operation layer must not claim real/paper-scale training")
        if self.network_scope not in {"localhost_only", "none"}:
            raise ValueError(f"unsupported network_scope {self.network_scope!r}")
        return self


class OperationSpec(BaseModel):
    """Backend-agnostic description of a tiny DiLoCo operation.

    A spec is intentionally minimal: it captures the inner/outer optimizer
    choice, learner topology, and synthetic-trainer wiring needed to run the
    decoupled-DiLoCo path on any backend.
    """

    model_config = ConfigDict(frozen=True)

    operation_schema_version: int = 1
    name: str = "tiny-diloco-operation"
    inner_optimizer: str = "adamw"
    outer_optimizer: str = "nesterov"
    outer_lr: float = Field(default=0.5, ge=0.0)
    outer_momentum: float = Field(default=0.9, ge=0.0)
    learners: int = Field(default=2, ge=1)
    steps: int = Field(default=30, ge=1)
    min_quorum: int = Field(default=2, ge=1)
    local_steps_per_sync: int = Field(default=1, ge=1)
    fragments: int = Field(default=1, ge=1)
    vector_dim: int = Field(default=8, ge=1)
    seed: int = 123
    trainer_type: str = "tiny_adamw"
    trainer_config: dict[str, Any] = Field(default_factory=lambda: {"optimizer": "adamw"})
    syncer_checkpoint_interval_rounds: int = Field(default=1, ge=0)
    restart_syncer_after_round: int | None = None
    payload_storage_mode: str = "inline"
    checkpoint_storage_mode: str = "inline"
    merge_mode: str = "in_memory"
    global_update_storage_mode: str = "inline"
    inline_payload_max_bytes: int = Field(default=1_000_000, ge=1)
    chunk_size_bytes: int = Field(default=1024 * 1024, ge=1)
    artifact_transfer_mode: str = "bundle"
    production_step_tags: list[str] = Field(default_factory=list)
    safety: OperationSafetyEnvelope = Field(default_factory=OperationSafetyEnvelope)

    @classmethod
    def torch_causal_lm_profile(
        cls,
        *,
        name: str = "torch-causal-lm-diloco-operation",
        learners: int = 2,
        steps: int = 30,
        min_quorum: int = 2,
        local_steps_per_sync: int = 1,
        fragments: int = 1,
        seed: int = 123,
        device: str = "cuda",
        vocab_size: int = 64,
        seq_len: int = 16,
        batch_size: int = 4,
        d_model: int = 32,
        num_layers: int = 1,
        num_heads: int = 2,
        mlp_ratio: float = 2.0,
        learning_rate: float = 0.001,
        gradient_clip_norm: float | None = 1.0,
        dtype: str = "float32",
        outer_lr: float = 0.5,
        outer_momentum: float = 0.9,
        restart_syncer_after_round: int | None = None,
        payload_storage_mode: str = "inline",
        checkpoint_storage_mode: str = "inline",
        merge_mode: str = "in_memory",
        global_update_storage_mode: str = "inline",
        inline_payload_max_bytes: int = 1_000_000,
        chunk_size_mb: int = 1,
        artifact_transfer_mode: str = "bundle",
        production_step_tags: list[str] | None = None,
    ) -> OperationSpec:
        """Build an operation spec for the real torch causal-LM trainer path.

        This profile is small by default but uses the same trainer adapter and
        optimizer semantics that a GPU Lambda run would use. It does not imply
        paper-scale training; it simply makes the operation layer capable of
        representing a real model-training path.
        """
        from decodilo.trainer.torch_causal_lm import estimate_causal_lm_num_parameters

        vector_dim = estimate_causal_lm_num_parameters(
            vocab_size=vocab_size,
            seq_len=seq_len,
            d_model=d_model,
            num_layers=num_layers,
            mlp_ratio=mlp_ratio,
        )
        return cls(
            name=name,
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            outer_lr=outer_lr,
            outer_momentum=outer_momentum,
            learners=learners,
            steps=steps,
            min_quorum=min_quorum,
            local_steps_per_sync=local_steps_per_sync,
            fragments=fragments,
            vector_dim=vector_dim,
            seed=seed,
            trainer_type="torch_causal_lm",
            trainer_config={
                "optimizer": "adamw",
                "device": device,
                "vocab_size": vocab_size,
                "seq_len": seq_len,
                "batch_size": batch_size,
                "d_model": d_model,
                "num_layers": num_layers,
                "num_heads": num_heads,
                "mlp_ratio": mlp_ratio,
                "learning_rate": learning_rate,
                "gradient_clip_norm": gradient_clip_norm,
                "dtype": dtype,
                "real_model_training_claimed": True,
                "paper_scale_training_claimed": False,
            },
            restart_syncer_after_round=restart_syncer_after_round,
            payload_storage_mode=payload_storage_mode,
            checkpoint_storage_mode=checkpoint_storage_mode,
            merge_mode=merge_mode,
            global_update_storage_mode=global_update_storage_mode,
            inline_payload_max_bytes=inline_payload_max_bytes,
            chunk_size_bytes=chunk_size_bytes_from_mb(chunk_size_mb),
            artifact_transfer_mode=artifact_transfer_mode,
            production_step_tags=production_step_tags or [],
        )

    @model_validator(mode="after")
    def _validate(self) -> OperationSpec:
        validate_runtime_modes(
            payload_storage_mode=self.payload_storage_mode,
            checkpoint_storage_mode=self.checkpoint_storage_mode,
            merge_mode=self.merge_mode,
            global_update_storage_mode=self.global_update_storage_mode,
        )
        if self.artifact_transfer_mode not in {"bundle", "object_store"}:
            raise ValueError(f"unsupported artifact_transfer_mode {self.artifact_transfer_mode!r}")
        if self.min_quorum > self.learners:
            raise ValueError("min_quorum cannot exceed learners")
        if self.inner_optimizer != "adamw":
            raise ValueError("only inner_optimizer='adamw' is supported in this slice")
        if self.outer_optimizer not in {"sgd", "nesterov"}:
            raise ValueError(f"unsupported outer_optimizer {self.outer_optimizer!r}")
        if self.trainer_type not in {"tiny_adamw", "torch_causal_lm"}:
            raise ValueError(
                "only trainer_type='tiny_adamw' or 'torch_causal_lm' is supported"
            )
        if self.trainer_type == "torch_causal_lm":
            if self.trainer_config.get("optimizer") != "adamw":
                raise ValueError("torch_causal_lm operation requires AdamW")
            if self.trainer_config.get("paper_scale_training_claimed") is True:
                raise ValueError("torch_causal_lm profile must not claim paper-scale training")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
