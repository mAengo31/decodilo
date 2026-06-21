from decodilo.scaling.failure_model import LearnerFailureModel
from decodilo.scaling.quorum_grace_sweep import sweep_quorum_grace


def test_quorum_grace_sweep_returns_pareto_candidates() -> None:
    result = sweep_quorum_grace(
        learner_count=8,
        quorum_candidates=[1, 4, 8],
        grace_window_seconds=[0, 5],
        failure_model=LearnerFailureModel(
            failure_rate_per_hour=0.02,
            recovery_time_seconds=300,
            training_duration_hours=24,
        ),
        speed_variance=0.2,
    )

    assert result.pareto_candidates
    assert any(
        "too_strict_quorum_failure_sensitive" in candidate.warning_flags
        for candidate in result.candidates
        if candidate.min_quorum == 8
    )
    assert any(
        "too_loose_quorum_low_sample_efficiency" in candidate.warning_flags
        for candidate in result.candidates
        if candidate.min_quorum == 1
    )

