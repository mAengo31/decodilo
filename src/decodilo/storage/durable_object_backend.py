"""Durable filesystem object-store backend for provider-shaped artifact testing.

This backend is intentionally local-filesystem based: it gives the runtime a
persistent object-store contract (stable refs, re-openable index, range reads,
idempotent puts) without claiming S3/GCS/R2 or performing network calls.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from decodilo.storage.artifact_backend import (
    ArtifactBackendCapabilities,
    ArtifactBackendRef,
)
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.content_addressed import ContentAddressedStore
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.range_reader import read_manifest_range
from decodilo.storage.remote_backend_contract import RemoteArtifactBackendCapabilities


class DurableFilesystemObjectStoreBackend:
    """Persistent object-store-shaped backend backed by local filesystem blobs."""

    def __init__(self, root: str | Path, *, namespace: str = "default") -> None:
        self.root = Path(root)
        self.namespace = namespace
        self.objects_root = self.root / "objects"
        self.store = ContentAddressedStore(self.objects_root)
        self.index_path = self.root / "artifact_index.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict[str, Any]] = self._load_index()

    def capabilities(self) -> ArtifactBackendCapabilities:
        return ArtifactBackendCapabilities(
            backend_type="durable_filesystem_object_store",
            local_filesystem=True,
            remote=False,
            read_supported=True,
            write_supported=True,
            list_supported=True,
            credentials_required=False,
        )

    def remote_capabilities(self) -> RemoteArtifactBackendCapabilities:
        return RemoteArtifactBackendCapabilities(
            backend_name="durable_filesystem_object_store",
            remote_backend_enabled=False,
            supports_range_read=True,
            supports_conditional_put=True,
            supports_strong_read_after_write=True,
            supports_atomic_manifest_commit=True,
            supports_object_versioning=True,
            supports_server_side_encryption=False,
            supports_client_side_encryption=False,
            supports_lifecycle_rules=True,
            supports_delete_transactions=False,
            supports_idempotent_put=True,
            supports_idempotent_delete=True,
            supports_integrity_metadata=True,
            supports_auth_scopes=False,
            supports_bandwidth_accounting=True,
            supports_cost_accounting=False,
        )

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef:
        digest = self.store.put_bytes(data)
        existing = self._index.get(artifact_id)
        if existing and existing.get("sha256") == digest:
            return self._ref_from_record(artifact_id, existing)
        version = 1 if existing is None else int(existing.get("version", 0)) + 1
        record = {
            "sha256": digest,
            "total_bytes": len(data),
            "version": version,
            "namespace": self.namespace,
        }
        self._index[artifact_id] = record
        self._write_index()
        return self._ref_from_record(artifact_id, record)

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes:
        self._validate_ref_backend(ref)
        record = self._record_for(ref)
        data = self.store.get_bytes(str(record["sha256"]))
        if sha256_bytes(data) != record["sha256"]:
            raise ValueError("durable object checksum mismatch")
        return data

    def list_refs(self) -> list[ArtifactBackendRef]:
        return [
            self._ref_from_record(artifact_id, record)
            for artifact_id, record in sorted(self._index.items())
        ]

    def iter_chunks(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> Iterator[bytes]:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            yield self.read_bytes(ref_or_manifest)
            return
        store = ChunkStore(chunk_root or self.objects_root)
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
        if offset < 0 or length <= 0:
            raise ValueError("invalid artifact range")
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            data = self.read_bytes(ref_or_manifest)
            if offset + length > len(data):
                raise ValueError("invalid artifact range")
            return data[offset : offset + length]
        return read_manifest_range(
            manifest=ref_or_manifest,
            chunk_root=chunk_root or self.objects_root,
            offset=offset,
            length=length,
        ).data

    def validate_manifest(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | Path | None = None,
    ) -> None:
        ChunkStore(chunk_root or self.objects_root).verify_manifest(manifest)

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
            return int(self._record_for(ref_or_manifest)["total_bytes"])
        return ref_or_manifest.total_bytes

    def delete_ref(self, ref: ArtifactBackendRef) -> None:
        self._validate_ref_backend(ref)
        self._index.pop(ref.artifact_id, None)
        self._write_index()

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if not self.index_path.exists():
            return {}
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("durable object index must be a JSON object")
        return {str(key): dict(value) for key, value in payload.items()}

    def _write_index(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._index, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, self.index_path)

    def _ref_from_record(self, artifact_id: str, record: dict[str, Any]) -> ArtifactBackendRef:
        digest = str(record["sha256"])
        return ArtifactBackendRef(
            backend_type="durable_filesystem_object_store",
            uri=f"durablefs://{self.namespace}/{artifact_id}@{record['version']}",
            artifact_id=artifact_id,
            metadata={
                "sha256": digest,
                "total_bytes": int(record["total_bytes"]),
                "version": int(record["version"]),
                "namespace": self.namespace,
                "path": str(self.store.path_for_hash(digest)),
            },
        )

    def _validate_ref_backend(self, ref: ArtifactBackendRef) -> None:
        if ref.backend_type != "durable_filesystem_object_store":
            raise ValueError(f"unsupported backend_type {ref.backend_type!r}")

    def _record_for(self, ref: ArtifactBackendRef) -> dict[str, Any]:
        record = self._index.get(ref.artifact_id)
        if record is None:
            raise KeyError(ref.artifact_id)
        expected_sha = str(ref.metadata.get("sha256"))
        if expected_sha and record.get("sha256") != expected_sha:
            raise ValueError("durable object ref sha256 mismatch")
        return record
