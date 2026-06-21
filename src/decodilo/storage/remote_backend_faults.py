"""Deterministic fault injection models for the remote backend simulator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendFaultConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    transient_put_failures: int = Field(default=0, ge=0)
    transient_get_failures: int = Field(default=0, ge=0)
    persistent_failure: bool = False
    corrupt_read_after: int | None = Field(default=None, ge=1)
    partial_write_failure: bool = False
    manifest_hash_mismatch: bool = False
    seed: int = 0


class RemoteBackendFaultState(BaseModel):
    model_config = ConfigDict(frozen=False)

    put_attempts: int = 0
    get_attempts: int = 0
    corruptions_triggered: int = 0

