"""Artifact backend pressure estimates for learner-pod scaling."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field


class ArtifactPressureEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    fragment_artifact_bytes_per_sync: float
    global_update_artifact_bytes_per_sync: float
    checkpoint_bytes_per_interval: float
    artifact_reads_per_second: float
    artifact_writes_per_second: float
    artifact_read_gbps_required: float
    artifact_write_gbps_required: float
    artifact_ops_per_second: float
    artifact_backend_saturation_ratio: float
    warnings: list[str] = Field(default_factory=list)


def estimate_artifact_pressure(
    *,
    learner_count: int,
    model_parameter_count: int,
    bytes_per_parameter: float,
    fragment_count: int,
    chunk_size_bytes: int,
    sync_interval_steps: int,
    local_step_seconds: float,
    checkpoint_interval_syncs: int = 10,
    artifact_backend_read_gbps: float | None = None,
    artifact_backend_write_gbps: float | None = None,
) -> ArtifactPressureEstimate:
    _validate_common(
        learner_count,
        model_parameter_count,
        bytes_per_parameter,
        fragment_count,
        chunk_size_bytes,
        sync_interval_steps,
        local_step_seconds,
    )
    model_bytes = model_parameter_count * bytes_per_parameter
    sync_seconds = sync_interval_steps * local_step_seconds
    fragment_bytes = learner_count * model_bytes
    update_bytes = learner_count * model_bytes
    checkpoint_bytes = (
        (learner_count + 1) * model_bytes * max(1, checkpoint_interval_syncs)
    )
    chunk_ops_per_model = max(1, math.ceil(model_bytes / chunk_size_bytes))
    write_ops = learner_count * chunk_ops_per_model / sync_seconds
    read_ops = (learner_count + 1) * chunk_ops_per_model / sync_seconds
    read_gbps = (fragment_bytes + update_bytes) * 8 / sync_seconds / 1_000_000_000
    write_gbps = (fragment_bytes + model_bytes) * 8 / sync_seconds / 1_000_000_000
    ratios = []
    warnings: list[str] = []
    if artifact_backend_read_gbps is not None:
        ratios.append(read_gbps / artifact_backend_read_gbps)
    else:
        warnings.append("artifact read capacity missing; using unsaturated planning default")
    if artifact_backend_write_gbps is not None:
        ratios.append(write_gbps / artifact_backend_write_gbps)
    else:
        warnings.append("artifact write capacity missing; using unsaturated planning default")
    saturation = max(ratios, default=0.0)
    if saturation > 1:
        warnings.append("artifact backend bandwidth cap exceeded")
    if chunk_size_bytes < 256 * 1024:
        warnings.append("small chunks increase artifact operation pressure")
    return ArtifactPressureEstimate(
        fragment_artifact_bytes_per_sync=fragment_bytes,
        global_update_artifact_bytes_per_sync=update_bytes,
        checkpoint_bytes_per_interval=checkpoint_bytes,
        artifact_reads_per_second=read_ops,
        artifact_writes_per_second=write_ops,
        artifact_read_gbps_required=read_gbps,
        artifact_write_gbps_required=write_gbps,
        artifact_ops_per_second=read_ops + write_ops,
        artifact_backend_saturation_ratio=saturation,
        warnings=warnings,
    )


def _validate_common(
    learner_count: int,
    model_parameter_count: int,
    bytes_per_parameter: float,
    fragment_count: int,
    chunk_size_bytes: int,
    sync_interval_steps: int,
    local_step_seconds: float,
) -> None:
    if min(learner_count, model_parameter_count, fragment_count, chunk_size_bytes) <= 0:
        raise ValueError("counts and sizes must be positive")
    if bytes_per_parameter <= 0 or sync_interval_steps <= 0 or local_step_seconds <= 0:
        raise ValueError("sizes and intervals must be positive")

