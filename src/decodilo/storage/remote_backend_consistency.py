"""Consistency controls for the local remote-backend simulator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendConsistencyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    strong_read_after_write: bool = True
    monotonic_manifest_visibility: bool = True
    visibility_delay_ticks: int = Field(default=0, ge=0)
    stale_list_ticks: int = Field(default=0, ge=0)
    object_versioning: bool = False


class RemoteBackendConsistencyObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    read_after_write_visible: bool
    list_visible: bool
    version: int
    logical_time: int

