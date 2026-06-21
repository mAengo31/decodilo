"""Heuristic algorithmic efficiency proxy for planning.

This module does not predict ML quality. It only exposes a bounded planning proxy
so scaling reports can make staleness and quorum tradeoffs explicit.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AlgorithmicEfficiencyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    outer_merge_rule: str = "token_weighted_average"
    token_weighting_enabled: bool = True
    rda_enabled: bool = False
    outer_merge_stability_profile: str | None = None
    heuristic_label: str = "heuristic_planning_proxy_not_ml_quality_prediction"


class AlgorithmicEfficiencyEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_efficiency_multiplier: float
    staleness_penalty: float
    quorum_noise_penalty: float
    heterogeneity_penalty: float
    merge_rule_stability_adjustment: float
    warnings: list[str] = Field(default_factory=list)
    heuristic: bool = True


def estimate_algorithmic_efficiency(
    *,
    learner_count: int,
    min_quorum: int,
    grace_window_seconds: float,
    sync_interval_steps: int,
    max_staleness_versions: int,
    accepted_contribution_ratio: float,
    learner_speed_variance: float,
    policy: AlgorithmicEfficiencyPolicy | None = None,
) -> AlgorithmicEfficiencyEstimate:
    if learner_count <= 0 or min_quorum <= 0 or min_quorum > learner_count:
        raise ValueError("learner_count and min_quorum must be valid")
    if min(sync_interval_steps, max_staleness_versions) < 0 or grace_window_seconds < 0:
        raise ValueError("intervals, staleness, and grace must be nonnegative")
    if learner_speed_variance < 0 or not 0 <= accepted_contribution_ratio <= 1:
        raise ValueError("variance and accepted contribution must be valid")
    active_policy = policy or AlgorithmicEfficiencyPolicy()
    quorum_ratio = min_quorum / learner_count
    quorum_noise_penalty = max(0.0, (0.5 - quorum_ratio) * 0.6)
    staleness_penalty = min(0.45, max_staleness_versions * 0.04 + sync_interval_steps / 50_000)
    heterogeneity_base = min(0.35, learner_speed_variance * (1.0 - quorum_ratio))
    heterogeneity_penalty = heterogeneity_base * (
        0.45 if active_policy.token_weighting_enabled else 1.0
    )
    merge_adjustment = 0.04 if active_policy.rda_enabled else 0.0
    grace_penalty = min(0.08, grace_window_seconds / 500)
    contribution_penalty = max(0.0, 0.8 - accepted_contribution_ratio) * 0.2
    multiplier = (
        1.0
        - quorum_noise_penalty
        - staleness_penalty
        - heterogeneity_penalty
        - grace_penalty
        - contribution_penalty
        + merge_adjustment
    )
    multiplier = max(0.05, min(1.05, multiplier))
    warnings: list[str] = ["algorithmic efficiency is a heuristic planning proxy"]
    if quorum_ratio < 0.4:
        warnings.append("low quorum ratio may reduce sample efficiency")
    if max_staleness_versions > 5:
        warnings.append("high staleness extrapolates beyond local validation")
    if learner_count > 128:
        warnings.append("large learner count is extrapolated")
    if not active_policy.rda_enabled and active_policy.outer_merge_stability_profile == "rda":
        warnings.append("RDA profile requested but RDA is not implemented")
    return AlgorithmicEfficiencyEstimate(
        sample_efficiency_multiplier=multiplier,
        staleness_penalty=staleness_penalty,
        quorum_noise_penalty=quorum_noise_penalty,
        heterogeneity_penalty=heterogeneity_penalty,
        merge_rule_stability_adjustment=merge_adjustment,
        warnings=warnings,
    )

