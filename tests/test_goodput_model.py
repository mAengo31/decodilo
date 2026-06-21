from decodilo.scaling.failure_model import LearnerFailureModel
from decodilo.scaling.goodput_model import build_goodput_curve, estimate_goodput


def test_goodput_distinguishes_raw_and_useful_tokens() -> None:
    failure = LearnerFailureModel(
        failure_rate_per_hour=0.2,
        recovery_time_seconds=300,
        training_duration_hours=2,
    )

    estimate = estimate_goodput(
        learner_count=4,
        min_quorum=2,
        per_learner_token_rate=100,
        failure_model=failure,
    )

    assert estimate.raw_tokens_per_second == 400
    assert 0 <= estimate.useful_tokens_per_second <= estimate.raw_tokens_per_second


def test_goodput_curve_is_ordered_by_input_counts() -> None:
    failure = LearnerFailureModel(
        failure_rate_per_hour=0,
        recovery_time_seconds=300,
        training_duration_hours=2,
    )

    curve = build_goodput_curve(
        learner_counts=[1, 2, 4],
        min_quorum_ratio=0.5,
        per_learner_token_rate=10,
        failure_model=failure,
    )

    assert [estimate.learner_count for estimate in curve.estimates] == [1, 2, 4]

