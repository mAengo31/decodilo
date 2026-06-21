"""Syncer merge pressure estimates for learner-pod scaling."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field


class SyncerPressureEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    merge_bytes_read: float
    merge_bytes_written: float
    merge_blocks_processed: int
    syncer_merge_gbps_required: float
    syncer_cpu_pressure_proxy: float
    syncer_memory_working_set_bytes: int
    syncer_saturation_ratio: float
    warnings: list[str] = Field(default_factory=list)


def estimate_syncer_pressure(
    *,
    learner_count: int,
    model_parameter_count: int,
    bytes_per_parameter: float,
    chunk_size_bytes: int,
    sync_interval_steps: int,
    local_step_seconds: float,
    syncer_max_merge_gbps: float | None = None,
    max_working_bytes: int | None = None,
) -> SyncerPressureEstimate:
    if min(learner_count, model_parameter_count, chunk_size_bytes, sync_interval_steps) <= 0:
        raise ValueError("counts, chunks, and intervals must be positive")
    if bytes_per_parameter <= 0 or local_step_seconds <= 0:
        raise ValueError("sizes and seconds must be positive")
    model_bytes = model_parameter_count * bytes_per_parameter
    sync_seconds = sync_interval_steps * local_step_seconds
    read = learner_count * model_bytes
    written = model_bytes
    blocks = max(1, math.ceil(model_bytes / chunk_size_bytes))
    required = (read + written) * 8 / sync_seconds / 1_000_000_000
    saturation = required / syncer_max_merge_gbps if syncer_max_merge_gbps else 0.0
    working = int(chunk_size_bytes * (min(learner_count, 4) + 2))
    warnings: list[str] = []
    if syncer_max_merge_gbps is None:
        warnings.append("syncer merge cap missing; using unsaturated planning default")
    elif saturation > 1:
        warnings.append("syncer merge cap exceeded")
    if max_working_bytes is not None and working > max_working_bytes:
        warnings.append("estimated syncer working set exceeds memory budget")
        saturation = max(saturation, working / max_working_bytes)
    return SyncerPressureEstimate(
        merge_bytes_read=read,
        merge_bytes_written=written,
        merge_blocks_processed=blocks * learner_count,
        syncer_merge_gbps_required=required,
        syncer_cpu_pressure_proxy=blocks * learner_count / sync_seconds,
        syncer_memory_working_set_bytes=working,
        syncer_saturation_ratio=saturation,
        warnings=warnings,
    )

