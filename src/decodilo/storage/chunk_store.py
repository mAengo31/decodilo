"""Chunked artifact storage on top of content-addressed chunks."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from decodilo.pricing.provenance import utc_now_iso
from decodilo.storage.content_addressed import ContentAddressedStore
from decodilo.storage.errors import ArtifactManifestError
from decodilo.storage.manifest import (
    StorageArtifactManifest,
    make_artifact_manifest,
    validate_artifact_manifest,
)


class ChunkStore:
    """Local filesystem chunk store with deterministic manifests."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.cas = ContentAddressedStore(self.root)
        self.manifest_root = self.root / "manifests"
        self.manifest_root.mkdir(parents=True, exist_ok=True)

    def write_artifact(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        run_id: str,
        chunks: Iterable[bytes],
        chunk_size_bytes: int,
        metadata: dict | None = None,
        manifest_path: str | Path | None = None,
    ) -> StorageArtifactManifest:
        chunk_hashes: list[str] = []
        total_bytes = 0
        for chunk in chunks:
            total_bytes += len(chunk)
            chunk_hashes.append(self.cas.put_bytes(chunk))
        manifest = make_artifact_manifest(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            run_id=run_id,
            total_bytes=total_bytes,
            chunk_size_bytes=chunk_size_bytes,
            chunk_hashes=chunk_hashes,
            metadata=metadata,
            created_at_utc=utc_now_iso(),
        )
        if manifest_path is not None:
            self.write_manifest(manifest_path, manifest)
        return manifest

    def write_bytes(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        run_id: str,
        data: bytes,
        chunk_size_bytes: int = 1024 * 1024,
        metadata: dict | None = None,
        manifest_path: str | Path | None = None,
    ) -> StorageArtifactManifest:
        return self.write_artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            run_id=run_id,
            chunks=(
                data[index : index + chunk_size_bytes]
                for index in range(0, len(data), chunk_size_bytes)
            ),
            chunk_size_bytes=chunk_size_bytes,
            metadata=metadata,
            manifest_path=manifest_path,
        )

    def read_bytes(self, manifest: StorageArtifactManifest) -> bytes:
        self.verify_manifest(manifest)
        data = b"".join(self.cas.get_bytes(chunk_hash) for chunk_hash in manifest.chunk_hashes)
        if len(data) != manifest.total_bytes:
            raise ArtifactManifestError("artifact total byte count mismatch")
        return data

    def verify_manifest(self, manifest: StorageArtifactManifest) -> None:
        validate_artifact_manifest(manifest)
        total = 0
        for chunk_hash in manifest.chunk_hashes:
            total += len(self.cas.get_bytes(chunk_hash))
        if total != manifest.total_bytes:
            raise ArtifactManifestError("artifact total bytes do not match chunks")

    def write_manifest(self, path: str | Path, manifest: StorageArtifactManifest) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(manifest.stable_json() + "\n", encoding="utf-8")
        os.replace(tmp, target)

    def read_manifest(self, path: str | Path) -> StorageArtifactManifest:
        try:
            manifest = StorageArtifactManifest.model_validate_json(
                Path(path).read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise ArtifactManifestError(f"invalid artifact manifest: {exc}") from exc
        validate_artifact_manifest(manifest)
        return manifest

