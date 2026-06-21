from decodilo.scaling.algorithmic_efficiency_model import (
    AlgorithmicEfficiencyPolicy,
    estimate_algorithmic_efficiency,
)


def test_algorithmic_efficiency_penalizes_low_quorum_and_staleness() -> None:
    high_quorum = estimate_algorithmic_efficiency(
        learner_count=8,
        min_quorum=6,
        grace_window_seconds=0,
        sync_interval_steps=100,
        max_staleness_versions=1,
        accepted_contribution_ratio=0.9,
        learner_speed_variance=0.1,
    )
    low_quorum = estimate_algorithmic_efficiency(
        learner_count=8,
        min_quorum=2,
        grace_window_seconds=0,
        sync_interval_steps=100,
        max_staleness_versions=5,
        accepted_contribution_ratio=0.9,
        learner_speed_variance=0.1,
    )

    assert low_quorum.sample_efficiency_multiplier < high_quorum.sample_efficiency_multiplier
    assert low_quorum.heuristic is True


def test_token_weighting_reduces_heterogeneity_penalty() -> None:
    weighted = estimate_algorithmic_efficiency(
        learner_count=8,
        min_quorum=4,
        grace_window_seconds=0,
        sync_interval_steps=100,
        max_staleness_versions=1,
        accepted_contribution_ratio=0.9,
        learner_speed_variance=0.5,
        policy=AlgorithmicEfficiencyPolicy(token_weighting_enabled=True),
    )
    unweighted = estimate_algorithmic_efficiency(
        learner_count=8,
        min_quorum=4,
        grace_window_seconds=0,
        sync_interval_steps=100,
        max_staleness_versions=1,
        accepted_contribution_ratio=0.9,
        learner_speed_variance=0.5,
        policy=AlgorithmicEfficiencyPolicy(token_weighting_enabled=False),
    )

    assert weighted.heterogeneity_penalty < unweighted.heterogeneity_penalty

