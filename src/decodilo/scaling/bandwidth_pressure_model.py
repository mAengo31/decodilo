"""Bandwidth pressure estimates for learner-pod scaling."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.bandwidth import estimate_outer_loop_bandwidth


class BandwidthPressureEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    wan_bytes_per_sync: float
    average_bandwidth_gbps: float
    peak_bandwidth_gbps_estimate: float
    bandwidth_saturation_ratio: float
    compression_bits: int | None = None
    warnings: list[str] = Field(default_factory=list)


def estimate_bandwidth_pressure(
    *,
    learner_count: int,
    model_parameter_count: int,
    bytes_per_parameter: float,
    fragment_count: int,
    sync_interval_steps: int,
    local_step_seconds: float,
    bandwidth_cap_gbps: float | None = None,
    compression_bits: int | None = None,
) -> BandwidthPressureEstimate:
    estimate = estimate_outer_loop_bandwidth(
        parameter_count=model_parameter_count,
        bytes_per_parameter=bytes_per_parameter,
        num_learners=learner_count,
        num_fragments=fragment_count,
        sync_interval_steps=sync_interval_steps,
        local_step_seconds=local_step_seconds,
        compression_bits=compression_bits,
    )
    warnings: list[str] = []
    if bandwidth_cap_gbps is None:
        saturation = 0.0
        warnings.append("bandwidth cap missing; using unsaturated planning default")
    else:
        saturation = estimate.peak_bandwidth_gbps_estimate / bandwidth_cap_gbps
        if saturation > 1:
            warnings.append("bandwidth cap exceeded")
    if compression_bits is not None:
        warnings.append("compression_bits reduces bandwidth estimate but requires validation")
    return BandwidthPressureEstimate(
        wan_bytes_per_sync=estimate.aggregate_bytes_per_sync_round,
        average_bandwidth_gbps=estimate.average_bandwidth_gbps,
        peak_bandwidth_gbps_estimate=estimate.peak_bandwidth_gbps_estimate,
        bandwidth_saturation_ratio=saturation,
        compression_bits=compression_bits,
        warnings=warnings,
    )

