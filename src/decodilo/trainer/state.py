"""Typed trainer adapter state models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrainerConfig(BaseModel):
    """Configuration passed to local trainer adapters."""

    model_config = ConfigDict(frozen=True)

    vector_dim: int = Field(gt=0)
    learning_rate: float = Field(ge=0)
    throughput_tokens_per_step: int = Field(ge=0)
    target_vector: list[float] | None = None
    initial_vector: list[float] | None = None
    script: str | None = None
    device: str = "cpu"
    batch_size: int = Field(default=4, gt=0)
    vocab_size: int = Field(default=64, gt=1)
    seq_len: int = Field(default=16, gt=1)
    d_model: int = Field(default=32, gt=0)
    num_layers: int = Field(default=1, ge=0)
    num_heads: int = Field(default=2, gt=0)
    mlp_ratio: float = Field(default=2.0, gt=0)
    optimizer: str = "sgd"
    gradient_clip_norm: float | None = Field(default=None, gt=0)
    dtype: str = "float32"


class TrainerState(BaseModel):
    """Full trainer state for fake-model and future adapter implementations."""

    model_config = ConfigDict(frozen=True)

    codec_version: str = "v1"
    trainer_type: str
    run_id: str
    learner_id: str
    global_version: int = Field(ge=0)
    local_step: int = Field(ge=0)
    tokens_processed: int = Field(ge=0)
    tokens_since_last_sync: int = Field(ge=0)
    dtype: str
    shape: list[int]
    parameters: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    trainer_state_kind: str = "flat"
    tensor_manifest: dict[str, Any] | None = None
    flat_state_checksum: str | None = None
    named_state_checksum: str | None = None
    checksum: str


class TrainerFragment(BaseModel):
    """A typed state fragment suitable for transport or checkpointing."""

    model_config = ConfigDict(frozen=True)

    codec_version: str = "v1"
    trainer_type: str
    run_id: str
    learner_id: str
    fragment_id: int = Field(ge=0)
    global_version: int = Field(ge=0)
    dtype: str
    shape: list[int]
    data: list[float]
    tokens: int = Field(ge=0)
    checksum: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    trainer_state_kind: str = "flat"
    flat_fragment: dict[str, Any] | None = None
    tensor_manifest: dict[str, Any] | None = None


class TrainStepResult(BaseModel):
    """Result from one local training burst."""

    model_config = ConfigDict(frozen=True)

    local_steps: int = Field(ge=0)
    local_steps_completed: int | None = Field(default=None, ge=0)
    tokens_processed: int = Field(ge=0)
    tokens_since_last_sync: int = Field(ge=0)
    loss: float | None = None
    loss_before: float | None = None
    loss_after: float | None = None
    final_loss: float | None = None
    grad_norm: float | None = None
    num_parameters: int | None = Field(default=None, ge=0)
    wall_time_seconds: float | None = Field(default=None, ge=0)


class TrainerHealth(BaseModel):
    """Lightweight trainer health and accounting state."""

    model_config = ConfigDict(frozen=True)

    healthy: bool = True
    status: str = "alive"
    local_step: int = Field(ge=0)
    tokens_processed: int = Field(ge=0)
    tokens_since_last_sync: int = Field(ge=0)
    global_version: int = Field(ge=0)
    state_checksum: str
    state_bytes_estimate: int | None = Field(default=None, ge=0)
    num_parameters: int | None = Field(default=None, ge=0)
    final_loss: float | None = None
    final_eval_loss: float | None = None
    nonfinite_detected: bool = False
