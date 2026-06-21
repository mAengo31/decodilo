"""Deterministic learner failure and quorum availability estimates."""

from __future__ import annotations

import math
import random

from pydantic import BaseModel, ConfigDict, Field


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class LearnerFailureModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_rate_per_hour: float = Field(ge=0)
    recovery_time_seconds: float = Field(ge=0)
    preemption_rate_per_hour: float = Field(default=0.0, ge=0)
    learner_startup_time_seconds: float = Field(default=0.0, ge=0)
    training_duration_hours: float = Field(gt=0)

    def estimate(
        self,
        *,
        learner_count: int,
        min_quorum: int,
        grace_window_seconds: float = 0.0,
        speed_variance_coefficient: float = 0.0,
    ) -> LearnerAvailabilityEstimate:
        if learner_count <= 0:
            raise ValueError("learner_count must be positive")
        if min_quorum <= 0 or min_quorum > learner_count:
            raise ValueError("min_quorum must be in [1, learner_count]")
        if grace_window_seconds < 0 or speed_variance_coefficient < 0:
            raise ValueError("grace window and speed variance must be nonnegative")
        recovery_loss = _clamp(self.failure_rate_per_hour * self.recovery_time_seconds / 3600)
        preemption_loss = _clamp(
            self.preemption_rate_per_hour
            * (self.recovery_time_seconds + self.learner_startup_time_seconds)
            / 3600
        )
        startup_loss = _clamp(
            self.learner_startup_time_seconds / (self.training_duration_hours * 3600)
        )
        learner_alive_probability = _clamp(1.0 - recovery_loss - preemption_loss - startup_loss)
        quorum_availability = _binomial_at_least(
            learner_count,
            min_quorum,
            learner_alive_probability,
        )
        expected_alive_ratio = learner_alive_probability
        grace_relief = 1.0 - math.exp(-grace_window_seconds / 10.0) if grace_window_seconds else 0.0
        straggler_loss = _clamp(speed_variance_coefficient * (1.0 - 0.5 * grace_relief))
        accepted = _clamp(quorum_availability * expected_alive_ratio * (1.0 - straggler_loss))
        estimated_goodput = _clamp(accepted)
        return LearnerAvailabilityEstimate(
            learner_count=learner_count,
            min_quorum=min_quorum,
            raw_availability=learner_alive_probability,
            quorum_availability=quorum_availability,
            accepted_contribution_ratio=accepted,
            straggler_loss_ratio=straggler_loss,
            recovery_loss_ratio=recovery_loss,
            preemption_loss_ratio=preemption_loss,
            estimated_goodput_ratio=estimated_goodput,
        )

    def monte_carlo_estimate(
        self,
        *,
        learner_count: int,
        min_quorum: int,
        trials: int = 1000,
        random_seed: int = 0,
    ) -> LearnerAvailabilityEstimate:
        if trials <= 0:
            raise ValueError("trials must be positive")
        analytic = self.estimate(learner_count=learner_count, min_quorum=min_quorum)
        rng = random.Random(random_seed)
        quorum_hits = 0
        alive_sum = 0
        for _ in range(trials):
            alive = sum(
                1 for _ in range(learner_count) if rng.random() < analytic.raw_availability
            )
            alive_sum += alive
            if alive >= min_quorum:
                quorum_hits += 1
        raw = alive_sum / (trials * learner_count)
        quorum = quorum_hits / trials
        return analytic.model_copy(
            update={
                "raw_availability": raw,
                "quorum_availability": quorum,
                "accepted_contribution_ratio": _clamp(raw * quorum),
                "estimated_goodput_ratio": _clamp(raw * quorum),
            }
        )


class LearnerAvailabilityEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    min_quorum: int
    raw_availability: float
    quorum_availability: float
    accepted_contribution_ratio: float
    straggler_loss_ratio: float
    recovery_loss_ratio: float
    preemption_loss_ratio: float
    estimated_goodput_ratio: float


def _binomial_at_least(n: int, k: int, p: float) -> float:
    return _clamp(
        sum(math.comb(n, i) * (p**i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))
    )

