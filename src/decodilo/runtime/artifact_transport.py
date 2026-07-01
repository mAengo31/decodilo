"""Local shared-filesystem artifact references for runtime transport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.errors import InvariantViolation
from decodilo.storage.artifact_backend import ArtifactBackendRef
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.durable_object_backend import DurableFilesystemObjectStoreBackend
from decodilo.storage.errors import StorageError
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.s3_compatible_backend import S3CompatibleArtifactBackend

ArtifactStorageBackend: TypeAlias = Literal[
    "local_filesystem",
    "syncer_object_store",
    "durable_filesystem_object_store",
    "s3_compatible",
]


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
    storage_backend: ArtifactStorageBackend = "local_filesystem"
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
    storage_backend: ArtifactStorageBackend = "local_filesystem"
    durable_backend_root: str | None = None


class LocalArtifactTransport:
    """Creates and validates artifact refs under a local workdir."""

    def __init__(
        self,
        *,
        policy: ArtifactTransportPolicy,
        s3_backend: S3CompatibleArtifactBackend | None = None,
    ) -> None:
        self.policy = policy
        self.s3_backend = s3_backend
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
        ref_metadata = metadata or manifest.metadata
        ref = ArtifactRef(
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
            metadata=ref_metadata,
        )
        if ref.storage_backend == "durable_filesystem_object_store":
            self._mirror_to_durable_backend(ref, manifest, chunk_target)
        if ref.storage_backend == "s3_compatible":
            s3_metadata = self._mirror_to_s3_backend(ref, manifest, chunk_target)
            ref = ref.model_copy(update={"metadata": {**ref.metadata, **s3_metadata}})
        return ref

    def validate_ref(self, ref: ArtifactRef | dict[str, Any]) -> StorageArtifactManifest:
        artifact_ref = ref if isinstance(ref, ArtifactRef) else ArtifactRef.model_validate(ref)
        if artifact_ref.storage_backend not in {
            "local_filesystem",
            "syncer_object_store",
            "durable_filesystem_object_store",
            "s3_compatible",
        }:
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
        if artifact_ref.storage_backend == "durable_filesystem_object_store":
            self._validate_durable_backend_mirror(artifact_ref, manifest, chunk_root)
        if artifact_ref.storage_backend == "s3_compatible":
            self._validate_s3_backend_mirror(artifact_ref, manifest, chunk_root)
        return manifest


    def _require_s3_backend(self) -> S3CompatibleArtifactBackend:
        if self.s3_backend is None:
            raise InvariantViolation(
                "S3-compatible artifact storage requires an explicitly injected backend"
            )
        if not self.s3_backend.remote_capabilities().remote_backend_enabled:
            raise InvariantViolation("S3-compatible artifact storage backend is not enabled")
        return self.s3_backend

    def _artifact_backend_ref_to_json(self, ref: ArtifactBackendRef) -> dict[str, Any]:
        return ref.model_dump(mode="json")

    def _artifact_backend_ref_from_json(self, value: dict[str, Any]) -> ArtifactBackendRef:
        return ArtifactBackendRef.model_validate(value)

    def _durable_backend(self, *, run_id: str) -> DurableFilesystemObjectStoreBackend:
        root = (
            Path(self.policy.durable_backend_root).resolve()
            if self.policy.durable_backend_root is not None
            else (self.artifact_root / "durable_objects").resolve()
        )
        return DurableFilesystemObjectStoreBackend(root, namespace=run_id)

    def _manifest_bytes(self, manifest: StorageArtifactManifest) -> bytes:
        return (
            json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")

    def _manifest_object_id(self, artifact_id: str) -> str:
        return f"{artifact_id}:manifest"

    def _chunk_object_id(self, artifact_id: str, chunk_hash: str) -> str:
        return f"{artifact_id}:chunk:{chunk_hash}"

    def _mirror_to_durable_backend(
        self,
        ref: ArtifactRef,
        manifest: StorageArtifactManifest,
        chunk_root: Path,
    ) -> None:
        backend = self._durable_backend(run_id=manifest.run_id)
        backend.write_bytes(
            artifact_id=self._manifest_object_id(ref.artifact_id),
            data=self._manifest_bytes(manifest),
        )
        store = ChunkStore(chunk_root)
        for chunk_hash in manifest.chunk_hashes:
            backend.write_bytes(
                artifact_id=self._chunk_object_id(ref.artifact_id, chunk_hash),
                data=store.cas.get_bytes(chunk_hash),
            )

    def _validate_durable_backend_mirror(
        self,
        ref: ArtifactRef,
        manifest: StorageArtifactManifest,
        chunk_root: Path,
    ) -> None:
        backend = self._durable_backend(run_id=manifest.run_id)
        manifest_ref = next(
            (
                item
                for item in backend.list_refs()
                if item.artifact_id == self._manifest_object_id(ref.artifact_id)
            ),
            None,
        )
        if (
            manifest_ref is None
            or backend.read_bytes(manifest_ref) != self._manifest_bytes(manifest)
        ):
            raise InvariantViolation("durable artifact manifest mirror mismatch")
        store = ChunkStore(chunk_root)
        for chunk_hash in manifest.chunk_hashes:
            chunk_ref = next(
                (
                    item
                    for item in backend.list_refs()
                    if item.artifact_id == self._chunk_object_id(ref.artifact_id, chunk_hash)
                ),
                None,
            )
            if (
                chunk_ref is None
                or backend.read_bytes(chunk_ref) != store.cas.get_bytes(chunk_hash)
            ):
                raise InvariantViolation(f"durable artifact chunk mirror mismatch {chunk_hash}")


    def _mirror_to_s3_backend(
        self,
        ref: ArtifactRef,
        manifest: StorageArtifactManifest,
        chunk_root: Path,
    ) -> dict[str, Any]:
        backend = self._require_s3_backend()
        manifest_ref = backend.write_bytes(
            artifact_id=self._manifest_object_id(ref.artifact_id),
            data=self._manifest_bytes(manifest),
        )
        store = ChunkStore(chunk_root)
        chunk_refs = [
            backend.write_bytes(
                artifact_id=self._chunk_object_id(ref.artifact_id, chunk_hash),
                data=store.cas.get_bytes(chunk_hash),
            )
            for chunk_hash in manifest.chunk_hashes
        ]
        return {
            "s3_compatible_manifest_ref": self._artifact_backend_ref_to_json(manifest_ref),
            "s3_compatible_chunk_refs": [
                self._artifact_backend_ref_to_json(chunk_ref) for chunk_ref in chunk_refs
            ],
            "s3_compatible_chunk_hashes": list(manifest.chunk_hashes),
        }

    def _validate_s3_backend_mirror(
        self,
        ref: ArtifactRef,
        manifest: StorageArtifactManifest,
        chunk_root: Path,
    ) -> None:
        backend = self._require_s3_backend()
        manifest_ref_payload = ref.metadata.get("s3_compatible_manifest_ref")
        chunk_ref_payloads = ref.metadata.get("s3_compatible_chunk_refs")
        if not isinstance(manifest_ref_payload, dict) or not isinstance(chunk_ref_payloads, list):
            raise InvariantViolation("S3-compatible artifact ref mirror metadata is missing")
        manifest_ref = self._artifact_backend_ref_from_json(manifest_ref_payload)
        try:
            manifest_bytes = backend.read_bytes(manifest_ref)
        except Exception as exc:  # noqa: BLE001 - normalize provider/client failures
            raise InvariantViolation("S3-compatible artifact manifest mirror mismatch") from exc
        if manifest_bytes != self._manifest_bytes(manifest):
            raise InvariantViolation("S3-compatible artifact manifest mirror mismatch")
        if len(chunk_ref_payloads) != len(manifest.chunk_hashes):
            raise InvariantViolation("S3-compatible artifact chunk mirror count mismatch")
        store = ChunkStore(chunk_root)
        for chunk_hash, chunk_ref_payload in zip(
            manifest.chunk_hashes,
            chunk_ref_payloads,
            strict=True,
        ):
            if not isinstance(chunk_ref_payload, dict):
                raise InvariantViolation("S3-compatible artifact chunk ref metadata is invalid")
            chunk_ref = self._artifact_backend_ref_from_json(chunk_ref_payload)
            try:
                chunk_bytes = backend.read_bytes(chunk_ref)
            except Exception as exc:  # noqa: BLE001 - normalize provider/client failures
                raise InvariantViolation(
                    f"S3-compatible artifact chunk mirror mismatch {chunk_hash}"
                ) from exc
            if chunk_bytes != store.cas.get_bytes(chunk_hash):
                raise InvariantViolation(
                    f"S3-compatible artifact chunk mirror mismatch {chunk_hash}"
                )

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
