import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.tensor_artifact import write_tensor_artifact
from decodilo.syncer.out_of_core_merge import build_merge_plan, out_of_core_token_weighted_merge


def test_out_of_core_merge_peak_estimate_respects_budget(tmp_path) -> None:
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    values = np.arange(64, dtype=np.float32)
    ref = write_tensor_artifact(
        tensors={"fragment": values + 1},
        run_id="run",
        artifact_id="run:learner-0:fragment",
        artifact_type="trainer_fragment",
        transport=transport,
        manifest_path=tmp_path / "artifacts" / "f.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=16,
        created_by="learner-0",
        metadata={
            "fragment_id": 0,
            "global_version": 0,
            "tokens": 1,
            "learner_id": "learner-0",
            "dtype": str(values.dtype),
            "shape": list(values.shape),
        },
    ).model_dump(mode="json")
    plan = build_merge_plan(
        run_id="run",
        round_id="round",
        fragment_id=0,
        input_artifact_refs={"learner-0": ref},
        token_counts={"learner-0": 1},
        global_values=values,
        outer_lr=1.0,
        chunk_size_bytes=16,
        max_working_bytes=80,
    )

    result = out_of_core_token_weighted_merge(plan=plan, global_values=values, transport=transport)

    assert result.metrics.merge_peak_working_bytes_estimate <= 80

    with pytest.raises(InvariantViolation):
        out_of_core_token_weighted_merge(
            plan=plan.model_copy(update={"max_working_bytes": 1}),
            global_values=values,
            transport=transport,
        )
