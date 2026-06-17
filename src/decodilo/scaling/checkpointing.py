"""Checkpoint storage estimators."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from decodilo.scaling.model_size import estimate_total_model_state_bytes


@dataclass(frozen=True)
class CheckpointEstimate:
    global_checkpoint_size: float
    learner_checkpoint_size: float
    total_retained_checkpoint_bytes: float
    write_bandwidth_required: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def estimate_checkpointing(
    *,
    parameter_count: int,
    bytes_per_parameter: float,
    optimizer_multiplier: float,
    num_learners: int,
    checkpoint_interval_minutes: float,
    retention_count: int,
) -> CheckpointEstimate:
    if num_learners <= 0 or checkpoint_interval_minutes <= 0 or retention_count <= 0:
        raise ValueError("num_learners, interval, and retention must be positive")
    global_size = estimate_total_model_state_bytes(
        parameter_count,
        bytes_per_parameter,
        optimizer_multiplier,
    )
    learner_size = global_size
    retained = (global_size + learner_size * num_learners) * retention_count
    write_bandwidth = (global_size + learner_size * num_learners) / (
        checkpoint_interval_minutes * 60
    )
    return CheckpointEstimate(
        global_checkpoint_size=global_size,
        learner_checkpoint_size=learner_size,
        total_retained_checkpoint_bytes=retained,
        write_bandwidth_required=write_bandwidth,
    )

