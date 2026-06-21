import pytest

from decodilo.scaling.failure_model import LearnerFailureModel


def test_zero_failure_rate_gives_high_availability() -> None:
    model = LearnerFailureModel(
        failure_rate_per_hour=0,
        recovery_time_seconds=300,
        training_duration_hours=1,
    )

    estimate = model.estimate(learner_count=4, min_quorum=4)

    assert estimate.raw_availability == 1
    assert estimate.quorum_availability == 1


def test_higher_failure_rate_lowers_goodput() -> None:
    low = LearnerFailureModel(
        failure_rate_per_hour=0.01,
        recovery_time_seconds=300,
        training_duration_hours=1,
    ).estimate(learner_count=4, min_quorum=3)
    high = LearnerFailureModel(
        failure_rate_per_hour=1.0,
        recovery_time_seconds=300,
        training_duration_hours=1,
    ).estimate(learner_count=4, min_quorum=3)

    assert high.estimated_goodput_ratio < low.estimated_goodput_ratio


def test_more_learners_can_improve_quorum_availability() -> None:
    model = LearnerFailureModel(
        failure_rate_per_hour=0.2,
        recovery_time_seconds=600,
        training_duration_hours=4,
    )

    small = model.estimate(learner_count=2, min_quorum=2)
    larger = model.estimate(learner_count=4, min_quorum=2)

    assert larger.quorum_availability > small.quorum_availability


def test_monte_carlo_estimate_is_seed_deterministic() -> None:
    model = LearnerFailureModel(
        failure_rate_per_hour=0.2,
        recovery_time_seconds=600,
        training_duration_hours=4,
    )

    first = model.monte_carlo_estimate(
        learner_count=4,
        min_quorum=2,
        trials=100,
        random_seed=123,
    )
    second = model.monte_carlo_estimate(
        learner_count=4,
        min_quorum=2,
        trials=100,
        random_seed=123,
    )

    assert first == second


def test_invalid_failure_parameters_rejected() -> None:
    with pytest.raises(ValueError):
        LearnerFailureModel(
            failure_rate_per_hour=0.1,
            recovery_time_seconds=1,
            training_duration_hours=1,
        ).estimate(learner_count=2, min_quorum=3)

