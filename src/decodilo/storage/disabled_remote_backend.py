"""Disabled remote artifact backend placeholder."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from decodilo.storage.artifact_backend import (
    ArtifactBackendCapabilities,
    ArtifactBackendRef,
)
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.remote_backend_contract import RemoteArtifactBackendCapabilities


class RemoteBackendDisabledError(RuntimeError):
    """Raised when code attempts to use a remote artifact backend."""


class DisabledRemoteArtifactBackend:
    def capabilities(self) -> ArtifactBackendCapabilities:
        return ArtifactBackendCapabilities(
            backend_type="remote_disabled",
            local_filesystem=False,
            remote=True,
            read_supported=False,
            write_supported=False,
            list_supported=False,
            credentials_required=False,
        )

    def remote_capabilities(self) -> RemoteArtifactBackendCapabilities:
        return RemoteArtifactBackendCapabilities(
            backend_name="remote_disabled",
            remote_backend_enabled=False,
        )

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def list_refs(self) -> list[ArtifactBackendRef]:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def iter_chunks(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> Iterator[bytes]:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def read_range(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        offset: int,
        length: int,
        chunk_root: str | Path | None = None,
    ) -> bytes:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def validate_manifest(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def validate_chunks(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")

    def artifact_size(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> int:
        raise RemoteBackendDisabledError("remote artifact backend is disabled")
