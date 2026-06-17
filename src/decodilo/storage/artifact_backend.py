"""Artifact backend interfaces for future remote storage."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from decodilo.storage.manifest import StorageArtifactManifest


class ArtifactBackendCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_type: str
    local_filesystem: bool
    remote: bool
    read_supported: bool
    write_supported: bool
    list_supported: bool
    credentials_required: bool = False


class ArtifactBackendRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_type: str
    uri: str
    artifact_id: str
    metadata: dict = {}


class ArtifactBackend(Protocol):
    def capabilities(self) -> ArtifactBackendCapabilities: ...

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef: ...

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes: ...

    def list_refs(self) -> list[ArtifactBackendRef]: ...

    def iter_chunks(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> Iterator[bytes]: ...

    def read_range(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        offset: int,
        length: int,
        chunk_root: str | Path | None = None,
    ) -> bytes: ...

    def validate_manifest(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None: ...

    def validate_chunks(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None: ...

    def artifact_size(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> int: ...
