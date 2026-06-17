"""Streaming artifact writer for local chunk storage."""

from __future__ import annotations

from pathlib import Path

from decodilo.pricing.provenance import utc_now_iso
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest, make_artifact_manifest


class ArtifactWriter:
    """Incrementally writes bytes into content-addressed chunks."""

    def __init__(
        self,
        *,
        store: ChunkStore,
        artifact_id: str,
        artifact_type: str,
        run_id: str,
        chunk_size_bytes: int = 1024 * 1024,
        metadata: dict | None = None,
        manifest_path: str | Path | None = None,
    ) -> None:
        self.store = store
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.run_id = run_id
        self.chunk_size_bytes = chunk_size_bytes
        self.metadata = metadata or {}
        self.manifest_path = manifest_path
        self._buffer = bytearray()
        self._chunk_hashes: list[str] = []
        self._total_bytes = 0
        self._finished = False

    def write(self, data: bytes) -> None:
        if self._finished:
            raise RuntimeError("artifact writer is already finished")
        self._buffer.extend(data)
        while len(self._buffer) >= self.chunk_size_bytes:
            chunk = bytes(self._buffer[: self.chunk_size_bytes])
            del self._buffer[: self.chunk_size_bytes]
            self._write_chunk(chunk)

    def _write_chunk(self, chunk: bytes) -> None:
        self._total_bytes += len(chunk)
        self._chunk_hashes.append(self.store.cas.put_bytes(chunk))

    def finish(self) -> StorageArtifactManifest:
        if self._finished:
            raise RuntimeError("artifact writer is already finished")
        if self._buffer:
            self._write_chunk(bytes(self._buffer))
            self._buffer.clear()
        manifest = make_artifact_manifest(
            artifact_id=self.artifact_id,
            artifact_type=self.artifact_type,
            run_id=self.run_id,
            total_bytes=self._total_bytes,
            chunk_size_bytes=self.chunk_size_bytes,
            chunk_hashes=list(self._chunk_hashes),
            metadata=self.metadata,
            created_at_utc=utc_now_iso(),
        )
        if self.manifest_path is not None:
            self.store.write_manifest(self.manifest_path, manifest)
        self._finished = True
        return manifest


def write_binary_artifact(
    *,
    store: ChunkStore,
    data: bytes,
    artifact_id: str,
    artifact_type: str,
    run_id: str,
    chunk_size_bytes: int = 1024 * 1024,
    metadata: dict | None = None,
    manifest_path: str | Path | None = None,
) -> StorageArtifactManifest:
    writer = ArtifactWriter(
        store=store,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        run_id=run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata=metadata,
        manifest_path=manifest_path,
    )
    writer.write(data)
    return writer.finish()
