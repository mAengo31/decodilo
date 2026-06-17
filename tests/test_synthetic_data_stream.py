import numpy as np

from decodilo.trainer.synthetic_data import make_synthetic_regression_batch


def test_synthetic_data_stream_is_deterministic() -> None:
    first = make_synthetic_regression_batch(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        local_step=0,
        batch_size=2,
        input_dim=3,
        output_dim=3,
        token_count=9,
    )
    second = make_synthetic_regression_batch(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        local_step=0,
        batch_size=2,
        input_dim=3,
        output_dim=3,
        token_count=9,
    )

    np.testing.assert_array_equal(first.inputs, second.inputs)
    np.testing.assert_array_equal(first.targets, second.targets)
    assert first.token_count == 9


def test_synthetic_data_stream_changes_with_step() -> None:
    first = make_synthetic_regression_batch(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        local_step=0,
        batch_size=2,
        input_dim=3,
        output_dim=3,
    )
    second = make_synthetic_regression_batch(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        local_step=1,
        batch_size=2,
        input_dim=3,
        output_dim=3,
    )

    assert not np.array_equal(first.inputs, second.inputs)
