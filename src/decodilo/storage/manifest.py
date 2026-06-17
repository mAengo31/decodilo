"""Deterministic storage artifact manifests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.storage.checksums import sha256_json, stable_json
from decodilo.storage.errors import ArtifactManifestError

STORAGE_ARTIFACT_SCHEMA_VERSION = "v1"
STORAGE_CODEC_VERSION = "v1"


class StorageArtifactManifest(BaseModel):
    """Manifest for a binary-safe chunked artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_type: str
    schema_version: str = STORAGE_ARTIFACT_SCHEMA_VERSION
    run_id: str
    created_at_utc: str | None = None
    total_bytes: int = Field(ge=0)
    chunk_size_bytes: int = Field(gt=0)
    chunk_hashes: list[str]
    root_hash: str
    manifest_hash: str
    compression: str = "none"
    codec_version: str = STORAGE_CODEC_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _schema_is_known(cls, value: str) -> str:
        if value != STORAGE_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(f"unknown storage artifact schema {value!r}")
        return value

    @field_validator("codec_version")
    @classmethod
    def _codec_is_known(cls, value: str) -> str:
        if value != STORAGE_CODEC_VERSION:
            raise ValueError(f"unknown storage artifact codec {value!r}")
        return value

    def stable_json(self) -> str:
        return stable_json(self.model_dump(mode="json"))


def manifest_root_hash(
    *,
    artifact_id: str,
    total_bytes: int,
    chunk_hashes: list[str],
    metadata: dict[str, Any],
) -> str:
    return sha256_json(
        {
            "artifact_id": artifact_id,
            "chunk_hashes": chunk_hashes,
            "metadata": metadata,
            "total_bytes": total_bytes,
        }
    )


def manifest_hash_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload.pop("manifest_hash", None)
    return payload


def make_artifact_manifest(
    *,
    artifact_id: str,
    artifact_type: str,
    run_id: str,
    total_bytes: int,
    chunk_size_bytes: int,
    chunk_hashes: list[str],
    metadata: dict[str, Any] | None = None,
    created_at_utc: str | None = None,
    compression: str = "none",
) -> StorageArtifactManifest:
    meta = metadata or {}
    root_hash = manifest_root_hash(
        artifact_id=artifact_id,
        total_bytes=total_bytes,
        chunk_hashes=chunk_hashes,
        metadata=meta,
    )
    payload = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "schema_version": STORAGE_ARTIFACT_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "total_bytes": total_bytes,
        "chunk_size_bytes": chunk_size_bytes,
        "chunk_hashes": chunk_hashes,
        "root_hash": root_hash,
        "compression": compression,
        "codec_version": STORAGE_CODEC_VERSION,
        "metadata": meta,
    }
    payload["manifest_hash"] = sha256_json(manifest_hash_payload(payload))
    return StorageArtifactManifest.model_validate(payload)


def validate_artifact_manifest(manifest: StorageArtifactManifest) -> None:
    expected_root = manifest_root_hash(
        artifact_id=manifest.artifact_id,
        total_bytes=manifest.total_bytes,
        chunk_hashes=manifest.chunk_hashes,
        metadata=manifest.metadata,
    )
    if expected_root != manifest.root_hash:
        raise ArtifactManifestError("artifact manifest root_hash mismatch")
    expected_manifest = sha256_json(manifest_hash_payload(manifest.model_dump(mode="json")))
    if expected_manifest != manifest.manifest_hash:
        raise ArtifactManifestError("artifact manifest_hash mismatch")

