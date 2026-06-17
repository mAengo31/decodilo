import numpy as np
import pytest

from decodilo.syncer.merge_plan import MergePlan, normalized_token_weights
from decodilo.syncer.out_of_core_merge import logical_metadata_merge_plan


def test_merge_plan_serializes_stably_and_weights_exclude_zero_tokens() -> None:
    weights = normalized_token_weights({"a": 1, "b": 3, "zero": 0})
    plan = MergePlan(
        run_id="run",
        round_id="round",
        fragment_id=0,
        input_artifact_refs={},
        token_weights=weights,
        dtype="float32",
        shape=[4],
        total_elements=4,
        chunk_size_bytes=16,
        max_working_bytes=64,
    )

    assert weights == {"a": 0.25, "b": 0.75, "zero": 0.0}
    assert plan.stable_json() == plan.stable_json()


def test_merge_plan_rejects_unsupported_dtype() -> None:
    with pytest.raises(ValueError):
        MergePlan(
            run_id="run",
            round_id="round",
            fragment_id=0,
            input_artifact_refs={},
            token_weights={},
            dtype="int32",
            shape=[1],
            total_elements=1,
            chunk_size_bytes=4,
            max_working_bytes=16,
        )


def test_metadata_only_merge_plan_is_explicit_simulation() -> None:
    plan = logical_metadata_merge_plan(
        run_id="run",
        round_id="round",
        logical_bytes=1_000_000_000,
        max_working_bytes=1024 * 1024,
    )

    assert plan.simulation_only is True
    assert plan.numeric_merge_performed is False
    assert np.prod(plan.shape) >= 250_000_000
    assert "metadata-only" in " ".join(plan.notes)
