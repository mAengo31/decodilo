import numpy as np
import pytest

from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.tensor_artifact import write_tensor_artifact
from decodilo.syncer.out_of_core_merge import build_merge_plan, out_of_core_token_weighted_merge
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


def _run_case(tmp_path, *, learners: int, length: int, dtype: str, outer_lr: float) -> None:
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    rng = np.random.default_rng(learners * 1000 + length)
    np_dtype = np.dtype(dtype)
    global_values = rng.normal(size=length).astype(np_dtype)
    refs = {}
    deltas = []
    tokens = {}
    for index in range(learners):
        learner_id = f"learner-{index}"
        values = rng.normal(size=length).astype(np_dtype)
        token_count = 0 if index == learners - 1 and learners > 1 else index + 1
        ref = write_tensor_artifact(
            tensors={"fragment": values},
            run_id="run",
            artifact_id=f"run:{learner_id}:fragment",
            artifact_type="trainer_fragment",
            transport=transport,
            manifest_path=tmp_path / "artifacts" / f"{learner_id}.artifact.json",
            chunk_root=tmp_path / "artifacts" / "store",
            chunk_size_bytes=max(np_dtype.itemsize * 3, 1),
            created_by=learner_id,
            metadata={
                "fragment_id": 0,
                "global_version": 0,
                "tokens": token_count,
                "learner_id": learner_id,
                "dtype": str(values.dtype),
                "shape": list(values.shape),
            },
        )
        refs[learner_id] = ref.model_dump(mode="json")
        deltas.append(LearnerDelta(learner_id, values.astype(np.float64), token_count, 0))
        tokens[learner_id] = token_count
    plan = build_merge_plan(
        run_id="run",
        round_id="round",
        fragment_id=0,
        input_artifact_refs=refs,
        token_counts=tokens,
        global_values=global_values,
        outer_lr=outer_lr,
        chunk_size_bytes=32,
        max_working_bytes=max(np_dtype.itemsize * 5 * (learners + 3), 64),
    )
    actual = out_of_core_token_weighted_merge(
        plan=plan,
        global_values=global_values,
        transport=transport,
    )
    memory = token_weighted_merge(global_values.astype(np.float64), deltas)
    expected = global_values.astype(np.float64) + outer_lr * (
        memory.new_global_vector - global_values.astype(np.float64)
    )

    np.testing.assert_allclose(actual.new_values, expected, rtol=1e-3, atol=1e-5)


@pytest.mark.slow
def test_out_of_core_merge_differential_cases(tmp_path) -> None:
    case_id = 0
    for learners in (1, 2, 3, 5):
        for length in (1, 2, 17, 128):
            for dtype in ("float32", "float64"):
                for outer_lr in (0.0, 0.1, 1.0):
                    _run_case(
                        tmp_path / f"case-{case_id}",
                        learners=learners,
                        length=length,
                        dtype=dtype,
                        outer_lr=outer_lr,
                    )
                    case_id += 1
