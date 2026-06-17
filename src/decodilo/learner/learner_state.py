"""Learner island state."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from decodilo.errors import InvariantViolation
from decodilo.protocol.messages import LearnerStatus


@dataclass
class LearnerState:
    """Mutable state tracked by each local learner island."""

    learner_id: str
    local_step: int
    tokens_processed: int
    parameters: NDArray[np.float64]
    last_global_version_seen: int
    status: LearnerStatus
    throughput_tokens_per_step: int
    tokens_since_last_sync: int = 0
    uptime_ticks: int = 0
    paused_ticks: int = 0
    failed_ticks: int = 0
    baseline_throughput_tokens_per_step: int | None = None
    step_interval_ticks: int = 1
    recovered_at_global_version: int | None = None

    def __post_init__(self) -> None:
        self.parameters = np.asarray(self.parameters, dtype=np.float64)
        if self.parameters.ndim != 1 or self.parameters.size == 0:
            raise ValueError("parameters must be a non-empty 1D vector")
        if self.local_step < 0:
            raise InvariantViolation("learner local_step must be non-negative")
        if self.tokens_processed < 0:
            raise InvariantViolation("learner tokens_processed must be non-negative")
        if self.tokens_since_last_sync < 0:
            raise InvariantViolation("tokens_since_last_sync must be non-negative")
        if self.throughput_tokens_per_step < 0:
            raise ValueError("throughput_tokens_per_step must be non-negative")
        if self.step_interval_ticks <= 0:
            raise ValueError("step_interval_ticks must be positive")
        if self.baseline_throughput_tokens_per_step is None:
            self.baseline_throughput_tokens_per_step = self.throughput_tokens_per_step
