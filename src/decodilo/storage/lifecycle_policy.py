"""Artifact lifecycle policy models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ArtifactRetentionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    keep_latest_checkpoints: int = Field(default=1, ge=1)
    keep_latest_global_states: int = Field(default=1, ge=1)
    keep_event_segments_after_latest_snapshot: bool = True
    keep_failed_run_artifacts: bool = True
    delete_temporary_artifacts: bool = True
    dry_run: bool = True
    allow_incomplete: bool = False


class ArtifactLifecycleState(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    state: str
    reason: str

