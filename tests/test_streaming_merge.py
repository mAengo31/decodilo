import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.storage.checksums import sha256_bytes
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.streaming_merge import (
    StreamingLearnerFragment,
    metadata_only_merge_dry_run,
    streaming_token_weighted_merge,
    validate_streaming_fragment,
)
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


def test_streaming_merge_matches_in_memory_merge() -> None:
    global_values = np.asarray([0.0, 0.0, 0.0, 0.0])
    learners = {
        "a": np.asarray([1.0, 1.0, 1.0, 1.0]),
        "b": np.asarray([3.0, 3.0, 3.0, 3.0]),
    }
    tokens = {"a": 1, "b": 3}

    streaming = streaming_token_weighted_merge(
        global_values=global_values,
        learner_values=learners,
        token_counts=tokens,
        outer_lr=1.0,
        chunk_elements=2,
    )
    memory = token_weighted_merge(
        global_values,
        [
            LearnerDelta("a", learners["a"], 1, 0),
            LearnerDelta("b", learners["b"], 3, 0),
        ],
    )

    np.testing.assert_allclose(streaming.new_values, memory.new_global_vector)
    assert streaming.metrics.streaming_merge_chunks_processed == 2
    assert streaming.metrics.streaming_merge_bytes_read > 0
    assert streaming.numeric_merge_performed is True
    assert streaming.simulation_only is False


def test_streaming_merge_matches_in_memory_for_one_learner_and_outer_lr() -> None:
    global_values = np.asarray([1.0, 1.0])
    learner = np.asarray([3.0, 5.0])

    streaming = streaming_token_weighted_merge(
        global_values=global_values,
        learner_values={"a": learner},
        token_counts={"a": 7},
        outer_lr=0.25,
        chunk_elements=1,
    )
    memory = token_weighted_merge(
        global_values,
        [LearnerDelta("a", learner, 7, 0)],
        optimizer=SGDOuterOptimizer(outer_lr=0.25),
    )

    np.testing.assert_allclose(streaming.new_values, memory.new_global_vector)


def test_streaming_merge_unequal_weights_and_zero_token_have_expected_effect() -> None:
    global_values = np.asarray([0.0, 0.0])
    learners = {
        "small": np.asarray([10.0, 0.0]),
        "large": np.asarray([0.0, 10.0]),
        "zero": np.asarray([1000.0, 1000.0]),
    }
    tokens = {"small": 1, "large": 3, "zero": 0}

    streaming = streaming_token_weighted_merge(
        global_values=global_values,
        learner_values=learners,
        token_counts=tokens,
        outer_lr=1.0,
        chunk_elements=2,
    )

    np.testing.assert_allclose(streaming.new_values, np.asarray([2.5, 7.5]))
    assert streaming.token_weights["zero"] == 0.0


def test_streaming_merge_rejects_mismatch_and_corruption() -> None:
    with pytest.raises(InvariantViolation):
        streaming_token_weighted_merge(
            global_values=np.asarray([0.0, 0.0]),
            learner_values={"a": np.asarray([1.0])},
            token_counts={"a": 1},
        )

    with pytest.raises(InvariantViolation):
        streaming_token_weighted_merge(
            global_values=np.asarray([0.0, 0.0]),
            learner_values={"a": np.asarray(["not", "numeric"])},
            token_counts={"a": 1},
        )

    fragment = StreamingLearnerFragment(
        learner_id="a",
        chunks=[b"abc"],
        tokens=1,
        checksum=sha256_bytes(b"def"),
    )
    with pytest.raises(InvariantViolation, match="checksum"):
        validate_streaming_fragment(fragment)


def test_metadata_only_merge_dry_run_does_not_materialize() -> None:
    result = metadata_only_merge_dry_run(
        fragment_hashes={"a": "hash-a"},
        payload_bytes={"a": 1_000_000_000},
        token_counts={"a": 10},
    )

    assert result.metadata_only is True
    assert result.numeric_merge_performed is False
    assert result.simulation_only is True
    assert result.new_values is None
    assert result.metrics.streaming_merge_bytes_read == 1_000_000_000
