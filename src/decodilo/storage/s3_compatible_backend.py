"""S3-compatible artifact backend adapter with fail-closed client injection.

This module intentionally does not import boto3, read environment variables, or
perform implicit network calls. Production code must provide an already-created
S3-compatible client object; tests can inject a fake client with the same small
method surface.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from decodilo.storage.artifact_backend import ArtifactBackendCapabilities, ArtifactBackendRef
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.remote_backend_contract import RemoteArtifactBackendCapabilities


class S3CompatibleBackendNotConfigured(RuntimeError):
    """Raised when an S3-compatible backend is used without an injected client."""


class S3CompatibleBackendConfig(BaseModel):
    """Configuration for an S3-compatible object backend.

    Credential fields are symbolic references only. This config is safe to
    serialize into reports because it does not contain raw keys or tokens.
    """

    model_config = ConfigDict(frozen=True)

    endpoint_url: str
    bucket: str
    prefix: str = "decodilo-artifacts"
    region: str | None = None
    access_key_ref: str | None = None
    secret_key_ref: str | None = None
    session_token_ref: str | None = None
    server_side_encryption: str | None = None

    @field_validator("access_key_ref", "secret_key_ref", "session_token_ref")
    @classmethod
    def _reject_raw_secret_like_values(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "=" in value or re.search(r"[A-Za-z0-9_=/+.-]{80,}", value):
            raise ValueError("S3 credential fields must be symbolic refs, not raw secrets")
        return value


class S3CompatibleClient(Protocol):
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_object(self, **kwargs: Any) -> dict[str, Any]: ...


class S3CompatibleArtifactBackend:
    """Provider-shaped S3-compatible artifact backend.

    The backend is network-capable only through the injected client. Without a
    client, every mutating/read operation fails closed.
    """

    def __init__(
        self,
        config: S3CompatibleBackendConfig,
        *,
        client: S3CompatibleClient | None = None,
    ) -> None:
        self.config = config
        self.client = client

    def capabilities(self) -> ArtifactBackendCapabilities:
        configured = self.client is not None
        return ArtifactBackendCapabilities(
            backend_type="s3_compatible",
            local_filesystem=False,
            remote=True,
            read_supported=configured,
            write_supported=configured,
            list_supported=configured,
            credentials_required=True,
        )

    def remote_capabilities(self) -> RemoteArtifactBackendCapabilities:
        configured = self.client is not None
        return RemoteArtifactBackendCapabilities(
            backend_name="s3_compatible",
            remote_backend_enabled=configured,
            supports_range_read=True,
            supports_conditional_put=False,
            supports_strong_read_after_write=True,
            supports_atomic_manifest_commit=False,
            supports_object_versioning=True,
            supports_server_side_encryption=bool(self.config.server_side_encryption),
            supports_client_side_encryption=False,
            supports_lifecycle_rules=False,
            supports_delete_transactions=False,
            supports_idempotent_put=True,
            supports_idempotent_delete=True,
            supports_integrity_metadata=True,
            supports_auth_scopes=True,
            supports_bandwidth_accounting=False,
            supports_cost_accounting=False,
        )

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef:
        client = self._client()
        digest = sha256_bytes(data)
        key = self._key_for_artifact(artifact_id)
        metadata = {"sha256": digest, "total_bytes": str(len(data)), "artifact_id": artifact_id}
        kwargs: dict[str, Any] = {
            "Bucket": self.config.bucket,
            "Key": key,
            "Body": data,
            "Metadata": metadata,
        }
        if self.config.server_side_encryption:
            kwargs["ServerSideEncryption"] = self.config.server_side_encryption
        response = client.put_object(**kwargs)
        version = response.get("VersionId") or response.get("version_id") or "unversioned"
        return self._ref(
            artifact_id=artifact_id,
            key=key,
            digest=digest,
            total_bytes=len(data),
            version=version,
        )

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes:
        body = self._get_object(ref).get("Body")
        data = body.read() if hasattr(body, "read") else body
        if not isinstance(data, bytes):
            raise TypeError("S3-compatible client Body must be bytes or file-like bytes")
        expected = str(ref.metadata.get("sha256"))
        if expected and sha256_bytes(data) != expected:
            raise ValueError("S3-compatible object checksum mismatch")
        return data

    def list_refs(self) -> list[ArtifactBackendRef]:
        client = self._client()
        response = client.list_objects_v2(Bucket=self.config.bucket, Prefix=self._prefix())
        refs: list[ArtifactBackendRef] = []
        for item in response.get("Contents", []) or []:
            key = str(item.get("Key"))
            head = client.head_object(Bucket=self.config.bucket, Key=key)
            metadata = {str(k).lower(): str(v) for k, v in (head.get("Metadata") or {}).items()}
            artifact_id = metadata.get("artifact_id") or key.rsplit("/", 1)[-1]
            total_bytes = int(metadata.get("total_bytes", item.get("Size", 0)))
            digest = metadata.get("sha256", "")
            version = head.get("VersionId") or head.get("version_id") or "unversioned"
            refs.append(
                self._ref(
                    artifact_id=artifact_id,
                    key=key,
                    digest=digest,
                    total_bytes=total_bytes,
                    version=version,
                )
            )
        return refs

    def iter_chunks(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | None = None,
    ) -> Iterator[bytes]:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            yield self.read_bytes(ref_or_manifest)
            return
        raise NotImplementedError("manifest chunk iteration requires local chunk_root")

    def read_range(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        offset: int,
        length: int,
        chunk_root: str | None = None,
    ) -> bytes:
        if offset < 0 or length <= 0:
            raise ValueError("invalid artifact range")
        if not isinstance(ref_or_manifest, ArtifactBackendRef):
            raise NotImplementedError("manifest range reads require local chunk_root")
        end = offset + length - 1
        response = self._get_object(ref_or_manifest, range_header=f"bytes={offset}-{end}")
        body = response.get("Body")
        data = body.read() if hasattr(body, "read") else body
        if not isinstance(data, bytes):
            raise TypeError("S3-compatible client Body must be bytes or file-like bytes")
        if len(data) != length:
            raise ValueError("S3-compatible range read returned unexpected length")
        return data

    def validate_manifest(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | None = None,
    ) -> None:
        raise NotImplementedError("manifest validation is not supported for remote refs")

    def validate_chunks(
        self,
        manifest: StorageArtifactManifest,
        *,
        chunk_root: str | None = None,
    ) -> None:
        self.validate_manifest(manifest, chunk_root=chunk_root)

    def artifact_size(
        self,
        ref_or_manifest: ArtifactBackendRef | StorageArtifactManifest,
        *,
        chunk_root: str | None = None,
    ) -> int:
        if isinstance(ref_or_manifest, ArtifactBackendRef):
            return int(ref_or_manifest.metadata.get("total_bytes", 0))
        return ref_or_manifest.total_bytes

    def delete_ref(self, ref: ArtifactBackendRef) -> None:
        self._client().delete_object(Bucket=self.config.bucket, Key=self._key_from_ref(ref))

    def _client(self) -> S3CompatibleClient:
        if self.client is None:
            raise S3CompatibleBackendNotConfigured(
                "S3-compatible backend requires an explicitly injected client"
            )
        return self.client

    def _prefix(self) -> str:
        return self.config.prefix.strip("/")

    def _key_for_artifact(self, artifact_id: str) -> str:
        safe_id = artifact_id.strip("/").replace("..", "_")
        prefix = self._prefix()
        return f"{prefix}/{safe_id}" if prefix else safe_id

    def _key_from_ref(self, ref: ArtifactBackendRef) -> str:
        if ref.backend_type != "s3_compatible":
            raise ValueError(f"unsupported backend_type {ref.backend_type!r}")
        key = str(ref.metadata.get("key") or "")
        if not key:
            raise ValueError("S3-compatible ref missing key metadata")
        return key

    def _get_object(
        self,
        ref: ArtifactBackendRef,
        *,
        range_header: str | None = None,
    ) -> dict[str, Any]:
        key = self._key_from_ref(ref)
        kwargs: dict[str, Any] = {"Bucket": self.config.bucket, "Key": key}
        if range_header:
            kwargs["Range"] = range_header
        return self._client().get_object(**kwargs)

    def _ref(
        self,
        *,
        artifact_id: str,
        key: str,
        digest: str,
        total_bytes: int,
        version: object,
    ) -> ArtifactBackendRef:
        return ArtifactBackendRef(
            backend_type="s3_compatible",
            uri=f"s3://{self.config.bucket}/{key}",
            artifact_id=artifact_id,
            metadata={
                "bucket": self.config.bucket,
                "key": key,
                "sha256": digest,
                "total_bytes": total_bytes,
                "version": str(version),
                "endpoint_url": self.config.endpoint_url,
            },
        )
