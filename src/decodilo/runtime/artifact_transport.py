"""Local shared-filesystem artifact references for runtime transport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.errors import InvariantViolation
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import StorageError
from decodilo.storage.manifest import StorageArtifactManifest


class ArtifactRef(BaseModel):
    """JSON-serializable reference to a local chunked artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_type: str
    manifest_path: str
    chunk_root: str
    total_bytes: int = Field(ge=0)
    manifest_hash: str
    content_root_hash: str | None = None
    run_id: str
    created_by: str
    storage_backend: Literal["local_filesystem", "syncer_object_store"] = "local_filesystem"
    relative_to_workdir: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("manifest_path", "chunk_root")
    @classmethod
    def _reject_urls(cls, value: str) -> str:
        if "://" in value or value.startswith("file:"):
            raise ValueError("artifact refs must use local paths, not URLs")
        return value

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


class ArtifactTransportPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    workdir: str
    artifact_root: str | None = None
    allow_absolute_paths: bool = False
    storage_backend: Literal["local_filesystem", "syncer_object_store"] = "local_filesystem"


class LocalArtifactTransport:
    """Creates and validates artifact refs under a local workdir."""

    def __init__(self, *, policy: ArtifactTransportPolicy) -> None:
        self.policy = policy
        self.workdir = Path(policy.workdir).resolve()
        self.artifact_root = (
            Path(policy.artifact_root).resolve()
            if policy.artifact_root is not None
            else (self.workdir / "artifacts").resolve()
        )
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def _resolve_ref_path(self, value: str) -> Path:
        raw = Path(value)
        if raw.is_absolute():
            if not self.policy.allow_absolute_paths:
                raise InvariantViolation("absolute artifact paths are not allowed")
            resolved = raw.resolve()
        else:
            resolved = (self.workdir / raw).resolve()
        self._ensure_inside_allowed_root(resolved, label="artifact path")
        return resolved

    def _ensure_inside_allowed_root(self, path: Path, *, label: str) -> None:
        allowed_roots = [self.workdir, self.artifact_root]
        for root in allowed_roots:
            try:
                path.relative_to(root)
                return
            except ValueError:
                continue
        raise InvariantViolation(f"{label} escapes the configured workdir/artifact root")

    def _to_ref_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.workdir))
        except ValueError as exc:
            if not self.policy.allow_absolute_paths:
                raise InvariantViolation("artifact path is outside workdir") from exc
            return str(path.resolve())

    def make_ref(
        self,
        *,
        manifest: StorageArtifactManifest,
        manifest_path: str | Path,
        chunk_root: str | Path,
        created_by: str,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        manifest_target = Path(manifest_path).resolve()
        chunk_target = Path(chunk_root).resolve()
        self._ensure_inside_allowed_root(manifest_target, label="manifest_path")
        self._ensure_inside_allowed_root(chunk_target, label="chunk_root")
        return ArtifactRef(
            artifact_id=manifest.artifact_id,
            artifact_type=manifest.artifact_type,
            manifest_path=self._to_ref_path(manifest_target),
            chunk_root=self._to_ref_path(chunk_target),
            total_bytes=manifest.total_bytes,
            manifest_hash=manifest.manifest_hash,
            content_root_hash=manifest.root_hash,
            run_id=manifest.run_id,
            created_by=created_by,
            storage_backend=self.policy.storage_backend,
            relative_to_workdir=True,
            metadata=metadata or manifest.metadata,
        )

    def validate_ref(self, ref: ArtifactRef | dict[str, Any]) -> StorageArtifactManifest:
        artifact_ref = ref if isinstance(ref, ArtifactRef) else ArtifactRef.model_validate(ref)
        if artifact_ref.storage_backend not in {"local_filesystem", "syncer_object_store"}:
            raise InvariantViolation("unsupported artifact storage backend")
        manifest_path = self._resolve_ref_path(artifact_ref.manifest_path)
        chunk_root = self._resolve_ref_path(artifact_ref.chunk_root)
        if not manifest_path.exists() or not manifest_path.is_file():
            raise InvariantViolation("artifact manifest is missing or not a file")
        if not chunk_root.exists() or not chunk_root.is_dir():
            raise InvariantViolation("artifact chunk_root is missing or not a directory")
        store = ChunkStore(chunk_root)
        try:
            manifest = store.read_manifest(manifest_path)
            store.verify_manifest(manifest)
        except StorageError as exc:
            raise InvariantViolation(f"invalid artifact ref: {exc}") from exc
        if manifest.manifest_hash != artifact_ref.manifest_hash:
            raise InvariantViolation("artifact manifest_hash mismatch")
        if manifest.root_hash != artifact_ref.content_root_hash:
            raise InvariantViolation("artifact content root hash mismatch")
        if manifest.total_bytes != artifact_ref.total_bytes:
            raise InvariantViolation("artifact total_bytes mismatch")
        if manifest.run_id != artifact_ref.run_id:
            raise InvariantViolation("artifact run_id mismatch")
        return manifest

    def resolve_ref_paths(self, ref: ArtifactRef | dict[str, Any]) -> tuple[Path, Path]:
        """Return validated manifest and chunk-root paths for a local artifact ref."""

        artifact_ref = ref if isinstance(ref, ArtifactRef) else ArtifactRef.model_validate(ref)
        manifest_path = self._resolve_ref_path(artifact_ref.manifest_path)
        chunk_root = self._resolve_ref_path(artifact_ref.chunk_root)
        if not manifest_path.exists() or not manifest_path.is_file():
            raise InvariantViolation("artifact manifest is missing or not a file")
        if not chunk_root.exists() or not chunk_root.is_dir():
            raise InvariantViolation("artifact chunk_root is missing or not a directory")
        return manifest_path, chunk_root

    def read_bytes(self, ref: ArtifactRef | dict[str, Any]) -> bytes:
        artifact_ref = ref if isinstance(ref, ArtifactRef) else ArtifactRef.model_validate(ref)
        manifest = self.validate_ref(artifact_ref)
        _, chunk_root = self.resolve_ref_paths(artifact_ref)
        return ChunkStore(chunk_root).read_bytes(manifest)
