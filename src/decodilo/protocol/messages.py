"""Pydantic protocol messages exchanged by learner, syncer, and replay code."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LearnerStatus(str, Enum):
    """Runtime state for a learner island."""

    ALIVE = "alive"
    PAUSED = "paused"
    FAILED = "failed"


class ModelFragment(BaseModel):
    """A typed model-state fragment suitable for JSON logging."""

    model_config = ConfigDict(frozen=True)

    fragment_id: str
    global_version: int = Field(ge=0)
    vector_data: list[float]
    source_learner_id: str | None = None
    tokens_since_last_sync: int = Field(ge=0)
    created_at: int = Field(ge=0)

    @field_validator("vector_data")
    @classmethod
    def _non_empty_vector(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("vector_data must not be empty")
        return value


class LearnerHeartbeat(BaseModel):
    """Heartbeat emitted by a learner to describe liveness and local progress."""

    model_config = ConfigDict(frozen=True)

    learner_id: str
    local_step: int = Field(ge=0)
    tokens_processed: int = Field(ge=0)
    last_global_version_seen: int = Field(ge=0)
    status: LearnerStatus
    throughput_tokens_per_step: int = Field(ge=0)
    logical_time: int = Field(ge=0)


class QuorumDecision(BaseModel):
    """Decision produced when the syncer evaluates pending learner updates."""

    model_config = ConfigDict(frozen=True)

    should_commit: bool
    round_id: str | None = None
    current_tick: int = Field(ge=0)
    accepted_learner_ids: list[str] = Field(default_factory=list)
    rejected_learner_ids: dict[str, str] = Field(default_factory=dict)
    grace_started_at: int | None = None
    reason: str


class MergeDecision(BaseModel):
    """Committed merge metadata, including deterministic vectors for replay."""

    model_config = ConfigDict(frozen=True)

    round_id: str
    previous_global_version: int = Field(ge=0)
    new_global_version: int = Field(ge=1)
    accepted_learner_ids: list[str]
    token_weights: dict[str, float]
    useful_tokens: int = Field(ge=0)
    outer_optimizer: str = "sgd"
    outer_lr: float = Field(ge=0)
    old_global_vector: list[float]
    weighted_delta: list[float]
    new_global_vector: list[float]


class CheckpointRecord(BaseModel):
    """Minimal checkpoint manifest stored in the deterministic event stream."""

    model_config = ConfigDict(frozen=True)

    checkpoint_id: str
    global_version: int = Field(ge=0)
    logical_time: int = Field(ge=0)
    global_vector: list[float]
    metrics: dict[str, Any] = Field(default_factory=dict)
