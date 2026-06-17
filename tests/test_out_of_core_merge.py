import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.tensor_artifact import write_tensor_artifact
from decodilo.syncer.out_of_core_merge import build_merge_plan, out_of_core_token_weighted_merge
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


def _transport(tmp_path):
    return LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )


def _write_ref(tmp_path, transport, learner_id: str, values: np.ndarray, tokens: int) -> dict:
    return write_tensor_artifact(
        tensors={"fragment": values},
        run_id="run",
        artifact_id=f"run:{learner_id}:fragment",
        artifact_type="trainer_fragment",
        transport=transport,
        manifest_path=tmp_path / "artifacts" / f"{learner_id}.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=16,
        created_by=learner_id,
        metadata={
            "fragment_id": 0,
            "global_version": 0,
            "tokens": tokens,
            "learner_id": learner_id,
            "dtype": str(values.dtype),
            "shape": list(values.shape),
        },
    ).model_dump(mode="json")


def test_out_of_core_merge_matches_in_memory_and_writes_artifact(tmp_path) -> None:
    transport = _transport(tmp_path)
    global_values = np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    learners = {
        "a": np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float64),
        "b": np.asarray([4.0, 3.0, 2.0, 1.0], dtype=np.float64),
    }
    tokens = {"a": 1, "b": 3}
    refs = {
        learner_id: _write_ref(tmp_path, transport, learner_id, values, tokens[learner_id])
        for learner_id, values in learners.items()
    }
    plan = build_merge_plan(
        run_id="run",
        round_id="round-1",
        fragment_id=0,
        input_artifact_refs=refs,
        token_counts=tokens,
        global_values=global_values,
        outer_lr=0.5,
        chunk_size_bytes=16,
        max_working_bytes=8 * 2 * 5,
        output_artifact_target={
            "artifact_id": "out",
            "artifact_type": "global_vector",
            "manifest_path": str(tmp_path / "artifacts" / "out.artifact.json"),
            "chunk_root": str(tmp_path / "artifacts" / "out-store"),
            "global_version": 1,
        },
    )
    result = out_of_core_token_weighted_merge(
        plan=plan,
        global_values=global_values,
        transport=transport,
    )
    memory = token_weighted_merge(
        global_values,
        [LearnerDelta("a", learners["a"], 1, 0), LearnerDelta("b", learners["b"], 3, 0)],
    )
    expected = global_values + 0.5 * (memory.new_global_vector - global_values)

    np.testing.assert_allclose(result.new_values, expected)
    assert result.output_artifact_ref is not None
    assert transport.validate_ref(result.output_artifact_ref)
    assert result.metrics.merge_peak_working_bytes_estimate <= plan.max_working_bytes


def test_out_of_core_merge_rejects_too_small_budget_and_nonfinite(tmp_path) -> None:
    transport = _transport(tmp_path)
    global_values = np.asarray([0.0, 1.0], dtype=np.float32)
    ref = _write_ref(tmp_path, transport, "a", np.asarray([1.0, 2.0], dtype=np.float32), 1)
    plan = build_merge_plan(
        run_id="run",
        round_id="round-1",
        fragment_id=0,
        input_artifact_refs={"a": ref},
        token_counts={"a": 1},
        global_values=global_values,
        outer_lr=1.0,
        chunk_size_bytes=8,
        max_working_bytes=1,
    )
    with pytest.raises(InvariantViolation, match="too small"):
        out_of_core_token_weighted_merge(
            plan=plan,
            global_values=global_values,
            transport=transport,
        )

    bad_plan = plan.model_copy(update={"max_working_bytes": 64})
    with pytest.raises(InvariantViolation, match="non-finite"):
        out_of_core_token_weighted_merge(
            plan=bad_plan,
            global_values=np.asarray([np.nan, 1.0], dtype=np.float32),
            transport=transport,
        )
