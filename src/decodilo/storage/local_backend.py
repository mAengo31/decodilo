"""Local filesystem artifact backend implementation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from decodilo.storage.artifact_backend import (
    ArtifactBackendCapabilities,
    ArtifactBackendRef,
)
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.content_addressed import ContentAddressedStore
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.range_reader import read_manifest_range


class LocalFilesystemArtifactBackend:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.store = ContentAddressedStore(self.root)
        self._refs: list[ArtifactBackendRef] = []

    def capabilities(self) -> ArtifactBackendCapabilities:
        return ArtifactBackendCapabilities(
            backend_type="local_filesystem",
            local_filesystem=True,
            remote=False,
            read_supported=True,
            write_supported=True,
            list_supported=True,
        )

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef:
        digest = self.store.put_bytes(data)
        for existing in self._refs:
            if (
                existing.artifact_id == artifact_id
                and existing.metadata.get("sha256") == digest
            ):
                return existing
        ref = ArtifactBackendRef(
            backend_type="local_filesystem",
            uri=str(self.store.path_for_hash(digest)),
            artifact_id=artifact_id,
            metadata={"sha256": digest, "total_bytes": len(data)},
        )
        self._refs.append(ref)
        return ref

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes:
        return self.store.get_bytes(str(ref.metadata["sha256"]))

    def list_refs(self) -> list[ArtifactBackendRef]:
        return list(self._refs)

    def iter_chunks(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> Iterator[bytes]:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            yield self.read_bytes(ref_or_manifest)
            return
        store = ChunkStore(chunk_root or self.root)
        store.verify_manifest(ref_or_manifest)
        for chunk_hash in ref_or_manifest.chunk_hashes:
            yield store.cas.get_bytes(chunk_hash)

    def read_range(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        offset: int,
        length: int,
        chunk_root: str | Path | None = None,
    ) -> bytes:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            data = self.read_bytes(ref_or_manifest)
            if offset < 0 or length <= 0 or offset + length > len(data):
                raise ValueError("invalid artifact range")
            return data[offset : offset + length]
        return read_manifest_range(
            manifest=ref_or_manifest,
            chunk_root=chunk_root or self.root,
            offset=offset,
            length=length,
        ).data

    def validate_manifest(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None:
        ChunkStore(chunk_root or self.root).verify_manifest(manifest)

    def validate_chunks(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None:
        self.validate_manifest(manifest, chunk_root=chunk_root)

    def artifact_size(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> int:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            return int(
                ref_or_manifest.metadata.get(
                    "total_bytes",
                    len(self.read_bytes(ref_or_manifest)),
                )
            )
        return ref_or_manifest.total_bytes
