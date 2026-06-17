"""Range and chunk readers for local chunked artifacts."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest


class ArtifactRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    offset: int = Field(ge=0)
    length: int = Field(gt=0)

    @model_validator(mode="after")
    def _range_is_safe(self) -> ArtifactRange:
        if self.offset + self.length < self.offset:
            raise ValueError("artifact range overflows")
        return self


class ArtifactRangeReadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    offset: int
    length: int
    data: bytes
    chunk_hashes: list[str]
    bytes_read: int


class ArtifactChunkIterator:
    """Iterate artifact chunks while validating content-addressed hashes."""

    def __init__(self, *, manifest: StorageArtifactManifest, chunk_root: str | Path) -> None:
        self.manifest = manifest
        self.store = ChunkStore(chunk_root)

    def __iter__(self) -> Iterator[tuple[int, str, bytes]]:
        self.store.verify_manifest(self.manifest)
        for index, chunk_hash in enumerate(self.manifest.chunk_hashes):
            yield index, chunk_hash, self.store.cas.get_bytes(chunk_hash)


def _validate_bounds(manifest: StorageArtifactManifest, offset: int, length: int) -> None:
    ArtifactRange(offset=offset, length=length)
    if offset > manifest.total_bytes:
        raise InvariantViolation("artifact range offset is out of bounds")
    if offset + length > manifest.total_bytes:
        raise InvariantViolation("artifact range exceeds artifact size")


def iter_manifest_chunks(
    *,
    manifest: StorageArtifactManifest,
    chunk_root: str | Path,
) -> Iterator[tuple[int, str, bytes]]:
    yield from ArtifactChunkIterator(manifest=manifest, chunk_root=chunk_root)


def read_manifest_range(
    *,
    manifest: StorageArtifactManifest,
    chunk_root: str | Path,
    offset: int,
    length: int,
) -> ArtifactRangeReadResult:
    """Read a byte range without materializing the whole artifact."""

    _validate_bounds(manifest, offset, length)
    wanted_start = offset
    wanted_stop = offset + length
    position = 0
    output = bytearray()
    used_hashes: list[str] = []
    for _index, chunk_hash, chunk in iter_manifest_chunks(manifest=manifest, chunk_root=chunk_root):
        chunk_start = position
        chunk_stop = position + len(chunk)
        position = chunk_stop
        if chunk_stop <= wanted_start:
            continue
        if chunk_start >= wanted_stop:
            break
        start = max(wanted_start - chunk_start, 0)
        stop = min(wanted_stop - chunk_start, len(chunk))
        output.extend(chunk[start:stop])
        used_hashes.append(chunk_hash)
    data = bytes(output)
    if len(data) != length:
        raise InvariantViolation("artifact range read returned incomplete data")
    return ArtifactRangeReadResult(
        offset=offset,
        length=length,
        data=data,
        chunk_hashes=used_hashes,
        bytes_read=len(data),
    )


def read_ref_range(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
    offset: int,
    length: int,
) -> ArtifactRangeReadResult:
    manifest = transport.validate_ref(ref)
    _manifest_path, chunk_root = transport.resolve_ref_paths(ref)
    return read_manifest_range(
        manifest=manifest,
        chunk_root=chunk_root,
        offset=offset,
        length=length,
    )


def artifact_size(*, ref: ArtifactRef | dict, transport: LocalArtifactTransport) -> int:
    return transport.validate_ref(ref).total_bytes
