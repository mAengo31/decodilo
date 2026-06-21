"""Goodput estimates for learner-pod scaling candidates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.failure_model import LearnerAvailabilityEstimate, LearnerFailureModel


class GoodputEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    min_quorum: int
    raw_tokens_per_second: float
    accepted_tokens_per_second: float
    useful_tokens_per_second: float
    raw_availability: float
    quorum_availability: float
    accepted_contribution_ratio: float
    straggler_loss_ratio: float
    recovery_loss_ratio: float
    preemption_loss_ratio: float
    estimated_goodput_ratio: float


class GoodputCurve(BaseModel):
    model_config = ConfigDict(frozen=True)

    estimates: list[GoodputEstimate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def estimate_goodput(
    *,
    learner_count: int,
    min_quorum: int,
    per_learner_token_rate: float,
    failure_model: LearnerFailureModel,
    grace_window_seconds: float = 0.0,
    speed_variance_coefficient: float = 0.0,
) -> GoodputEstimate:
    if per_learner_token_rate < 0:
        raise ValueError("per_learner_token_rate must be nonnegative")
    availability = failure_model.estimate(
        learner_count=learner_count,
        min_quorum=min_quorum,
        grace_window_seconds=grace_window_seconds,
        speed_variance_coefficient=speed_variance_coefficient,
    )
    raw = learner_count * per_learner_token_rate
    accepted = raw * availability.accepted_contribution_ratio
    useful = raw * availability.estimated_goodput_ratio
    return _from_availability(availability, raw, accepted, useful)


def build_goodput_curve(
    *,
    learner_counts: list[int],
    min_quorum_ratio: float,
    per_learner_token_rate: float,
    failure_model: LearnerFailureModel,
) -> GoodputCurve:
    if not 0 < min_quorum_ratio <= 1:
        raise ValueError("min_quorum_ratio must be in (0, 1]")
    estimates = [
        estimate_goodput(
            learner_count=count,
            min_quorum=max(1, round(count * min_quorum_ratio)),
            per_learner_token_rate=per_learner_token_rate,
            failure_model=failure_model,
        )
        for count in learner_counts
    ]
    return GoodputCurve(estimates=estimates)


def _from_availability(
    availability: LearnerAvailabilityEstimate,
    raw_tokens_per_second: float,
    accepted_tokens_per_second: float,
    useful_tokens_per_second: float,
) -> GoodputEstimate:
    return GoodputEstimate(
        learner_count=availability.learner_count,
        min_quorum=availability.min_quorum,
        raw_tokens_per_second=raw_tokens_per_second,
        accepted_tokens_per_second=accepted_tokens_per_second,
        useful_tokens_per_second=useful_tokens_per_second,
        raw_availability=availability.raw_availability,
        quorum_availability=availability.quorum_availability,
        accepted_contribution_ratio=availability.accepted_contribution_ratio,
        straggler_loss_ratio=availability.straggler_loss_ratio,
        recovery_loss_ratio=availability.recovery_loss_ratio,
        preemption_loss_ratio=availability.preemption_loss_ratio,
        estimated_goodput_ratio=availability.estimated_goodput_ratio,
    )

