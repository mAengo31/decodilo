import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.tensor_artifact import read_tensor_artifact, write_tensor_artifact


def _transport(tmp_path):
    return LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )


def test_binary_tensor_artifact_roundtrip_and_corruption_rejected(tmp_path) -> None:
    transport = _transport(tmp_path)
    ref = write_tensor_artifact(
        tensors={"weights": np.asarray([1.0, 2.0, 3.0], dtype=np.float32)},
        run_id="run",
        artifact_id="artifact",
        artifact_type="tensor_state",
        transport=transport,
        manifest_path=tmp_path / "artifacts" / "weights.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=8,
        created_by="test",
    )

    decoded, metadata = read_tensor_artifact(ref=ref, transport=transport)

    np.testing.assert_array_equal(decoded["weights"], np.asarray([1.0, 2.0, 3.0], dtype=np.float32))
    assert metadata.codec == "tensor_binary_v1"
    assert ref.metadata["codec"] == "tensor_binary_v1"

    manifest_path = tmp_path / ref.manifest_path
    text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(text.replace('"total_bytes"', '"tampered_total_bytes"', 1))
    with pytest.raises(InvariantViolation):
        transport.validate_ref(ref)
