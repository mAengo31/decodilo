"""Replay index models used to choose genesis or snapshot replay."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReplayMode = Literal["genesis", "snapshot"]


class ReplayStartPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: ReplayMode
    snapshot_path: str | None = None
    segment_manifest_path: str | None = None
    start_after_event_id: str | None = None
    start_after_logical_time: int = Field(default=0, ge=0)


class ReplayIndex(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    event_log_path: str | None = None
    segment_manifest_path: str | None = None
    latest_snapshot_path: str | None = None
    start_points: list[ReplayStartPoint] = Field(default_factory=list)

