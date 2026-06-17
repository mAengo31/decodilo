import pytest

from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import ChunkCorruptionError, ChunkMissingError


def test_chunk_store_write_read_and_verify_roundtrip(tmp_path) -> None:
    store = ChunkStore(tmp_path)
    manifest = store.write_bytes(
        artifact_id="artifact-1",
        artifact_type="binary",
        run_id="run",
        data=b"abcdef" * 10,
        chunk_size_bytes=7,
        manifest_path=tmp_path / "manifests" / "artifact.json",
    )

    assert store.read_bytes(manifest) == b"abcdef" * 10
    store.verify_manifest(manifest)
    assert (tmp_path / "manifests" / "artifact.json").exists()


def test_chunk_store_rejects_missing_and_corrupted_chunks(tmp_path) -> None:
    store = ChunkStore(tmp_path)
    manifest = store.write_bytes(
        artifact_id="artifact-1",
        artifact_type="binary",
        run_id="run",
        data=b"abcdef",
        chunk_size_bytes=3,
    )
    first = manifest.chunk_hashes[0]
    store.cas.delete(first)
    with pytest.raises(ChunkMissingError):
        store.read_bytes(manifest)

    manifest = store.write_bytes(
        artifact_id="artifact-2",
        artifact_type="binary",
        run_id="run",
        data=b"abcdef",
        chunk_size_bytes=3,
    )
    path = store.cas.path_for_hash(manifest.chunk_hashes[0])
    path.write_bytes(b"bad")
    with pytest.raises(ChunkCorruptionError):
        store.read_bytes(manifest)

