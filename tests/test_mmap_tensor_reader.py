import numpy as np
import pytest

from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import ChunkMissingError
from decodilo.storage.mmap_reader import MMapTensorArtifactReader
from decodilo.storage.tensor_artifact import write_tensor_artifact


def test_mmap_reader_iterates_validates_and_reconstructs(tmp_path) -> None:
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    ref = write_tensor_artifact(
        tensors={"x": np.arange(10, dtype=np.float64)},
        run_id="run",
        artifact_id="x",
        artifact_type="tensor",
        transport=transport,
        manifest_path=tmp_path / "artifacts" / "x.artifact.json",
        chunk_root=tmp_path / "artifacts" / "store",
        chunk_size_bytes=16,
        created_by="test",
    )
    manifest = ChunkStore(tmp_path / "artifacts" / "store").read_manifest(
        tmp_path / ref.manifest_path
    )
    reader = MMapTensorArtifactReader(
        chunk_root=tmp_path / "artifacts" / "store",
        manifest=manifest,
    )

    chunks = list(reader.iter_tensor_chunks())
    decoded, _ = reader.read_tensors()

    assert len(chunks) == len(manifest.chunk_hashes)
    assert reader.stats.bytes_read >= manifest.total_bytes
    assert reader.stats.chunks_read >= len(manifest.chunk_hashes)
    assert isinstance(reader.stats.mmap_used, bool)
    np.testing.assert_array_equal(decoded["x"], np.arange(10, dtype=np.float64))

    ChunkStore(tmp_path / "artifacts" / "store").cas.delete(manifest.chunk_hashes[0])
    with pytest.raises(ChunkMissingError):
        MMapTensorArtifactReader(
            chunk_root=tmp_path / "artifacts" / "store",
            manifest=manifest,
        ).validate_only()
