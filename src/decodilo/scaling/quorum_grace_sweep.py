"""Quorum and grace-window sweep for learner-pod planning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from decodilo.scaling.algorithmic_efficiency_model import estimate_algorithmic_efficiency
from decodilo.scaling.failure_model import LearnerFailureModel


class QuorumGraceCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_quorum: int
    grace_window_seconds: float
    estimated_goodput: float
    estimated_sample_efficiency: float
    accepted_contribution_ratio: float
    straggler_loss: float
    expected_sync_rounds: float
    warning_flags: list[str] = Field(default_factory=list)
    pareto_efficient: bool = False


class QuorumGraceSweepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_count: int
    candidates: list[QuorumGraceCandidate]
    pareto_candidates: list[QuorumGraceCandidate]
    warnings: list[str] = Field(default_factory=list)


def sweep_quorum_grace(
    *,
    learner_count: int,
    quorum_candidates: list[int],
    grace_window_seconds: list[float],
    failure_model: LearnerFailureModel,
    speed_variance: float,
    sync_interval_steps: int = 500,
    local_step_seconds: float = 1.0,
) -> QuorumGraceSweepResult:
    if learner_count <= 0:
        raise ValueError("learner_count must be positive")
    candidates: list[QuorumGraceCandidate] = []
    for quorum in quorum_candidates:
        if quorum <= 0 or quorum > learner_count:
            raise ValueError("quorum candidate must be in [1, learner_count]")
        for grace in grace_window_seconds:
            availability = failure_model.estimate(
                learner_count=learner_count,
                min_quorum=quorum,
                grace_window_seconds=grace,
                speed_variance_coefficient=speed_variance,
            )
            algo = estimate_algorithmic_efficiency(
                learner_count=learner_count,
                min_quorum=quorum,
                grace_window_seconds=grace,
                sync_interval_steps=sync_interval_steps,
                max_staleness_versions=1,
                accepted_contribution_ratio=availability.accepted_contribution_ratio,
                learner_speed_variance=speed_variance,
            )
            flags: list[str] = []
            if quorum == learner_count:
                flags.append("too_strict_quorum_failure_sensitive")
            if quorum == 1 or quorum / learner_count < 0.35:
                flags.append("too_loose_quorum_low_sample_efficiency")
            if grace > 0 and speed_variance < 0.05:
                flags.append("grace_window_may_hurt_wall_clock_efficiency")
            if grace > 0 and speed_variance >= 0.05:
                flags.append("grace_window_may_improve_sample_efficiency")
            candidates.append(
                QuorumGraceCandidate(
                    min_quorum=quorum,
                    grace_window_seconds=grace,
                    estimated_goodput=availability.estimated_goodput_ratio
                    * algo.sample_efficiency_multiplier,
                    estimated_sample_efficiency=algo.sample_efficiency_multiplier,
                    accepted_contribution_ratio=availability.accepted_contribution_ratio,
                    straggler_loss=availability.straggler_loss_ratio,
                    expected_sync_rounds=3600 / (sync_interval_steps * local_step_seconds),
                    warning_flags=[*flags, *algo.warnings],
                )
            )
    pareto = _pareto(candidates)
    marked = [
        candidate.model_copy(update={"pareto_efficient": candidate in pareto})
        for candidate in candidates
    ]
    marked_pareto = [candidate for candidate in marked if candidate.pareto_efficient]
    return QuorumGraceSweepResult(
        learner_count=learner_count,
        candidates=marked,
        pareto_candidates=marked_pareto,
    )


def _pareto(candidates: list[QuorumGraceCandidate]) -> list[QuorumGraceCandidate]:
    result: list[QuorumGraceCandidate] = []
    for candidate in candidates:
        dominated = False
        for other in candidates:
            if other is candidate:
                continue
            if (
                other.estimated_goodput >= candidate.estimated_goodput
                and other.estimated_sample_efficiency
                >= candidate.estimated_sample_efficiency
                and (
                    other.estimated_goodput > candidate.estimated_goodput
                    or other.estimated_sample_efficiency
                    > candidate.estimated_sample_efficiency
                )
            ):
                dominated = True
                break
        if not dominated:
            result.append(candidate)
    return result

