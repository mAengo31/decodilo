import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.syncer.binary_streaming_merge import binary_streaming_token_weighted_merge
from decodilo.syncer.outer_optimizer import SGDOuterOptimizer
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge
from decodilo.trainer.fragment_artifacts import write_fragment_artifact
from decodilo.trainer.state_codec import make_fragment


def _write_fragment(
    tmp_path,
    learner_id: str,
    values: np.ndarray,
    tokens: int,
) -> tuple[dict, LocalArtifactTransport]:
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    fragment = make_fragment(
        trainer_type="numpy_convex",
        run_id="run",
        learner_id=learner_id,
        fragment_id=0,
        global_version=0,
        data=values,
        tokens=tokens,
    )
    ref = write_fragment_artifact(
        fragment=fragment,
        transport=transport,
        manifest_path=tmp_path / "artifacts" / f"{learner_id}.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=8,
        created_by=learner_id,
        codec="binary_v1",
    )
    return ref.model_dump(mode="json"), transport


def test_binary_streaming_merge_matches_in_memory_with_weights_and_outer_lr(tmp_path) -> None:
    global_values = np.asarray([0.0, 0.0, 0.0, 0.0])
    ref_a, transport = _write_fragment(tmp_path, "a", np.asarray([1.0, 1.0, 1.0, 1.0]), 1)
    ref_b, _ = _write_fragment(tmp_path, "b", np.asarray([3.0, 3.0, 3.0, 3.0]), 3)
    ref_zero, _ = _write_fragment(tmp_path, "zero", np.asarray([100.0, 100.0, 100.0, 100.0]), 0)

    binary = binary_streaming_token_weighted_merge(
        global_values=global_values,
        fragment_refs={"a": ref_a, "b": ref_b, "zero": ref_zero},
        token_counts={"a": 1, "b": 3, "zero": 0},
        transport=transport,
        outer_lr=0.5,
        chunk_elements=2,
    )
    memory = token_weighted_merge(
        global_values,
        [
            LearnerDelta("a", np.asarray([1.0, 1.0, 1.0, 1.0]), 1, 0),
            LearnerDelta("b", np.asarray([3.0, 3.0, 3.0, 3.0]), 3, 0),
            LearnerDelta("zero", np.asarray([100.0, 100.0, 100.0, 100.0]), 0, 0),
        ],
        optimizer=SGDOuterOptimizer(outer_lr=0.5),
    )

    np.testing.assert_allclose(binary.result.new_values, memory.new_global_vector)
    assert binary.bytes_read > 0
    assert binary.chunks_read > 0
    assert binary.wall_time_seconds >= 0.0


def test_binary_streaming_merge_rejects_corrupt_artifact(tmp_path) -> None:
    ref, transport = _write_fragment(tmp_path, "a", np.asarray([1.0, 2.0]), 1)
    manifest_path = tmp_path / ref["manifest_path"]
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace('"total_bytes"', '"bad"', 1),
        encoding="utf-8",
    )

    with pytest.raises(InvariantViolation):
        binary_streaming_token_weighted_merge(
            global_values=np.asarray([0.0, 0.0]),
            fragment_refs={"a": ref},
            token_counts={"a": 1},
            transport=transport,
        )
