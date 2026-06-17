"""CPU-only learner island for synchronization mechanics tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from decodilo.errors import InvariantViolation
from decodilo.learner.learner_state import LearnerState
from decodilo.protocol.messages import LearnerHeartbeat, LearnerStatus


@dataclass
class LearnerUpdate:
    learner_id: str
    vector: NDArray[np.float64]
    global_version_seen: int
    tokens: int


class FakeLearner:
    """A deterministic local optimizer over a convex quadratic objective."""

    def __init__(self, state: LearnerState, *, learning_rate: float = 0.05) -> None:
        self.state = state
        self.learning_rate = learning_rate
        if learning_rate < 0:
            raise ValueError("learning_rate must be non-negative")

    def tick(self, *, target_vector: NDArray[np.float64]) -> None:
        target = np.asarray(target_vector, dtype=np.float64)
        if target.shape != self.state.parameters.shape:
            raise ValueError("target_vector shape must match learner parameters")

        previous_step = self.state.local_step
        previous_tokens = self.state.tokens_processed
        if self.state.status == LearnerStatus.ALIVE:
            self.state.uptime_ticks += 1
            if (self.state.uptime_ticks - 1) % self.state.step_interval_ticks != 0:
                return
            gradient = 2.0 * (self.state.parameters - target)
            self.state.parameters = self.state.parameters - self.learning_rate * gradient
            self.state.local_step += 1
            self.state.tokens_processed += self.state.throughput_tokens_per_step
            self.state.tokens_since_last_sync += self.state.throughput_tokens_per_step
        elif self.state.status == LearnerStatus.PAUSED:
            self.state.paused_ticks += 1
        else:
            self.state.failed_ticks += 1

        if self.state.local_step < previous_step:
            raise InvariantViolation("learner local_step must be monotonic")
        if self.state.tokens_processed < previous_tokens:
            raise InvariantViolation("learner tokens_processed must be monotonic")
        if self.state.status != LearnerStatus.ALIVE and (
            self.state.local_step != previous_step
            or self.state.tokens_processed != previous_tokens
        ):
            raise InvariantViolation("paused or failed learners must not process steps")

    def make_update(self) -> LearnerUpdate:
        update = LearnerUpdate(
            learner_id=self.state.learner_id,
            vector=self.state.parameters.copy(),
            global_version_seen=self.state.last_global_version_seen,
            tokens=self.state.tokens_since_last_sync,
        )
        return update

    def mark_update_accepted(self) -> None:
        """Clear local contribution tokens only after a committed sync uses them."""

        self.state.tokens_since_last_sync = 0

    def receive_global(self, vector: NDArray[np.float64], *, global_version: int) -> None:
        if global_version < self.state.last_global_version_seen:
            raise InvariantViolation("learner global version cannot move backwards")
        self.state.parameters = np.asarray(vector, dtype=np.float64).copy()
        self.state.last_global_version_seen = global_version

    def heartbeat(self, *, logical_time: int) -> LearnerHeartbeat:
        return LearnerHeartbeat(
            learner_id=self.state.learner_id,
            local_step=self.state.local_step,
            tokens_processed=self.state.tokens_processed,
            last_global_version_seen=self.state.last_global_version_seen,
            status=self.state.status,
            throughput_tokens_per_step=self.state.throughput_tokens_per_step,
            logical_time=logical_time,
        )

    def pause(self) -> None:
        if self.state.status == LearnerStatus.ALIVE:
            self.state.status = LearnerStatus.PAUSED

    def fail(self) -> None:
        self.state.status = LearnerStatus.FAILED

    def recover(self, *, recovery_version: int) -> None:
        if recovery_version < 0:
            raise ValueError("recovery_version must be non-negative")
        self.state.status = LearnerStatus.ALIVE
        self.state.recovered_at_global_version = recovery_version

    def slow(self, factor: float) -> None:
        if factor <= 0:
            raise ValueError("slow factor must be positive")
        baseline = (
            self.state.baseline_throughput_tokens_per_step
            or self.state.throughput_tokens_per_step
        )
        self.state.throughput_tokens_per_step = max(1, int(round(baseline * factor)))
        self.state.step_interval_ticks = max(1, int(round(1.0 / min(factor, 1.0))))

    def restore_speed(self) -> None:
        baseline = self.state.baseline_throughput_tokens_per_step
        if baseline is not None:
            self.state.throughput_tokens_per_step = baseline
        self.state.step_interval_ticks = 1
