import numpy as np

from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


def test_zero_token_learners_have_no_effect() -> None:
    global_vector = np.array([1.0, 1.0])
    result = token_weighted_merge(
        global_vector,
        [
            LearnerDelta("zero", np.array([100.0, 100.0]), 0, 0),
            LearnerDelta("useful", np.array([3.0, 1.0]), 10, 0),
        ],
    )

    np.testing.assert_allclose(result.new_global_vector, np.array([3.0, 1.0]))
    assert result.included_learner_ids == ["useful"]
    assert result.useful_tokens == 10


def test_larger_token_learner_has_proportionally_larger_influence() -> None:
    global_vector = np.array([0.0])
    result = token_weighted_merge(
        global_vector,
        [
            LearnerDelta("small", np.array([10.0]), 1, 0),
            LearnerDelta("large", np.array([20.0]), 3, 0),
        ],
    )

    np.testing.assert_allclose(result.weighted_delta, np.array([17.5]))
    np.testing.assert_allclose(result.new_global_vector, np.array([17.5]))
    assert result.token_weights == {"small": 0.25, "large": 0.75}


def test_identical_learners_produce_identical_merged_output() -> None:
    global_vector = np.array([0.0, 0.0])
    result = token_weighted_merge(
        global_vector,
        [
            LearnerDelta("a", np.array([2.0, 4.0]), 5, 0),
            LearnerDelta("b", np.array([2.0, 4.0]), 10, 0),
        ],
        optimizer=SGDOuterOptimizer(outer_lr=0.5),
    )

    np.testing.assert_allclose(result.new_global_vector, np.array([1.0, 2.0]))


def test_stale_learners_can_be_excluded() -> None:
    global_vector = np.array([0.0])
    result = token_weighted_merge(
        global_vector,
        [
            LearnerDelta("fresh", np.array([2.0]), 10, 2),
            LearnerDelta("stale", np.array([100.0]), 100, 0),
        ],
        excluded_learner_ids={"stale"},
    )

    np.testing.assert_allclose(result.new_global_vector, np.array([2.0]))
    assert result.included_learner_ids == ["fresh"]

