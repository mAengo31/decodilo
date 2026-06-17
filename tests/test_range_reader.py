import pytest

from decodilo.errors import InvariantViolation
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import ChunkMissingError
from decodilo.storage.range_reader import iter_manifest_chunks, read_manifest_range


def test_range_reader_reads_chunks_and_ranges(tmp_path) -> None:
    store = ChunkStore(tmp_path / "store")
    data = b"abcdefghijklmnopqrstuvwxyz"
    manifest = store.write_bytes(
        artifact_id="range",
        artifact_type="test",
        run_id="run",
        data=data,
        chunk_size_bytes=5,
        manifest_path=tmp_path / "manifest.json",
    )

    chunks = list(iter_manifest_chunks(manifest=manifest, chunk_root=tmp_path / "store"))
    result = read_manifest_range(
        manifest=manifest,
        chunk_root=tmp_path / "store",
        offset=3,
        length=10,
    )

    assert b"".join(chunk for _idx, _hash, chunk in chunks) == data
    assert result.data == data[3:13]
    assert result.bytes_read == 10


def test_range_reader_rejects_invalid_range_and_corruption(tmp_path) -> None:
    store = ChunkStore(tmp_path / "store")
    manifest = store.write_bytes(
        artifact_id="range",
        artifact_type="test",
        run_id="run",
        data=b"abcdef",
        chunk_size_bytes=3,
    )

    with pytest.raises(ValueError):
        read_manifest_range(manifest=manifest, chunk_root=tmp_path / "store", offset=0, length=0)
    with pytest.raises(InvariantViolation, match="exceeds"):
        read_manifest_range(manifest=manifest, chunk_root=tmp_path / "store", offset=4, length=4)

    store.cas.delete(manifest.chunk_hashes[0])
    with pytest.raises(ChunkMissingError):
        list(iter_manifest_chunks(manifest=manifest, chunk_root=tmp_path / "store"))
