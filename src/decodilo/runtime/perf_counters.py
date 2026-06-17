"""Lightweight non-replayable runtime performance counters."""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict, Field


class PerfCounters(BaseModel):
    model_config = ConfigDict(frozen=True)

    wall_time_seconds: float = Field(ge=0)
    learner_train_wall_time_seconds: float = Field(default=0.0, ge=0)
    learner_submit_wall_time_seconds: float = Field(default=0.0, ge=0)
    syncer_merge_wall_time_seconds: float = Field(default=0.0, ge=0)
    syncer_checkpoint_wall_time_seconds: float = Field(default=0.0, ge=0)
    artifact_write_wall_time_seconds: float = Field(default=0.0, ge=0)
    bytes_serialized: int = Field(default=0, ge=0)
    bytes_deserialized: int = Field(default=0, ge=0)
    transport_messages_sent: int = Field(default=0, ge=0)
    transport_messages_received: int = Field(default=0, ge=0)
    transport_bytes_sent: int = Field(default=0, ge=0)
    transport_bytes_received: int = Field(default=0, ge=0)
    peak_in_memory_bytes_estimate: int = Field(default=0, ge=0)
    spill_bytes_written: int = Field(default=0, ge=0)
    spill_bytes_read: int = Field(default=0, ge=0)


class PerfTimer:
    def __init__(self) -> None:
        self.started = time.monotonic()

    def elapsed(self) -> float:
        return max(time.monotonic() - self.started, 0.0)


def nonnegative_perf_counters(**kwargs) -> PerfCounters:
    defaults = {field: 0 for field in PerfCounters.model_fields}
    defaults["wall_time_seconds"] = 0.0
    defaults.update(kwargs)
    return PerfCounters.model_validate(defaults)

