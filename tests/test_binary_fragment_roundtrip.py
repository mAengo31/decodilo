import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.trainer.fragment_artifacts import read_fragment_artifact, write_fragment_artifact
from decodilo.trainer.state_codec import make_fragment


def test_binary_fragment_artifact_roundtrip_preserves_metadata(tmp_path) -> None:
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    fragment = make_fragment(
        trainer_type="numpy_convex",
        run_id="run",
        learner_id="learner-0",
        fragment_id=3,
        global_version=2,
        data=np.asarray([1.0, 2.0]),
        tokens=42,
    )
    ref = write_fragment_artifact(
        fragment=fragment,
        transport=transport,
        manifest_path=tmp_path / "artifacts" / "fragment.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=8,
        created_by="learner-0",
        codec="binary_v1",
    )

    restored = read_fragment_artifact(ref=ref, transport=transport)

    assert ref.metadata["codec"] == "tensor_binary_v1"
    assert restored.fragment_id == fragment.fragment_id
    assert restored.global_version == fragment.global_version
    assert restored.tokens == fragment.tokens
    np.testing.assert_allclose(restored.data, fragment.data)

    manifest_path = tmp_path / ref.manifest_path
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace('"tensor_checksum"', '"bad"', 1),
        encoding="utf-8",
    )
    with pytest.raises(InvariantViolation):
        read_fragment_artifact(ref=ref, transport=transport)
