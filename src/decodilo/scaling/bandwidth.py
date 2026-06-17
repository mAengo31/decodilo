"""WAN bandwidth estimator for outer-loop fragment exchange."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BandwidthEstimate:
    bytes_per_full_model: float
    bytes_per_fragment: float
    bytes_per_sync_round_per_learner: float
    aggregate_bytes_per_sync_round: float
    average_bandwidth_gbps: float
    peak_bandwidth_gbps_estimate: float
    notes: str

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def estimate_outer_loop_bandwidth(
    *,
    parameter_count: int,
    bytes_per_parameter: float,
    num_learners: int,
    num_fragments: int,
    sync_interval_steps: int,
    local_step_seconds: float,
    compression_bits: int | None = None,
    bidirectional: bool = True,
) -> BandwidthEstimate:
    if min(parameter_count, num_learners, num_fragments, sync_interval_steps) <= 0:
        raise ValueError("counts and intervals must be positive")
    if bytes_per_parameter <= 0 or local_step_seconds <= 0:
        raise ValueError("sizes and seconds must be positive")

    compression_ratio = 1.0
    if compression_bits is not None:
        if compression_bits <= 0:
            raise ValueError("compression_bits must be positive")
        compression_ratio = compression_bits / (bytes_per_parameter * 8)
    bytes_per_full_model = parameter_count * bytes_per_parameter * compression_ratio
    bytes_per_fragment = bytes_per_full_model / num_fragments
    direction_multiplier = 2 if bidirectional else 1
    per_learner = bytes_per_full_model * direction_multiplier
    aggregate = per_learner * num_learners
    sync_seconds = sync_interval_steps * local_step_seconds
    average_gbps = aggregate * 8 / sync_seconds / 1_000_000_000
    return BandwidthEstimate(
        bytes_per_full_model=bytes_per_full_model,
        bytes_per_fragment=bytes_per_fragment,
        bytes_per_sync_round_per_learner=per_learner,
        aggregate_bytes_per_sync_round=aggregate,
        average_bandwidth_gbps=average_gbps,
        peak_bandwidth_gbps_estimate=average_gbps * 2,
        notes="Outer-loop estimate only; excludes control messages and retries.",
    )

