"""S3-compatible artifact backend adapter with fail-closed client injection.

This module intentionally does not import boto3, read environment variables, or
perform implicit network calls. Production code must provide an already-created
S3-compatible client object; tests can inject a fake client with the same small
method surface.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class S3CompatiblePreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_type: str = "s3_compatible"
    status: Literal["blocked", "passed", "failed"]
    endpoint_url_present: bool
    bucket_present: bool
    prefix_present: bool
    symbolic_credentials_present: bool
    client_injected: bool
    probe_attempted: bool = False
    probe_passed: bool = False
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def preflight_s3_compatible_backend(
    config: S3CompatibleBackendConfig | None,
    *,
    client: S3CompatibleClient | None = None,
    require_probe: bool = False,
) -> S3CompatiblePreflightReport:
    blockers: list[str] = []
    warnings: list[str] = []
    if config is None:
        blockers.append("s3_config_missing")
        return S3CompatiblePreflightReport(
            status="blocked",
            endpoint_url_present=False,
            bucket_present=False,
            prefix_present=False,
            symbolic_credentials_present=False,
            client_injected=False,
            blockers=blockers,
            warnings=["S3-compatible backend is fail-closed until config is provided"],
        )

    endpoint_url_present = bool(config.endpoint_url)
    bucket_present = bool(config.bucket)
    prefix_present = bool(config.prefix)
    symbolic_credentials_present = bool(config.access_key_ref and config.secret_key_ref)
    if not endpoint_url_present:
        blockers.append("endpoint_url_missing")
    if not bucket_present:
        blockers.append("bucket_missing")
    if not symbolic_credentials_present:
        blockers.append("symbolic_credential_refs_missing")
    if client is None:
        blockers.append("client_not_injected")
    if require_probe and client is None:
        blockers.append("probe_required_but_client_missing")

    probe_attempted = False
    probe_passed = False
    if require_probe and client is not None and not blockers:
        probe_attempted = True
        try:
            client.list_objects_v2(Bucket=config.bucket, Prefix=config.prefix.strip("/"))
            probe_passed = True
        except Exception as exc:  # noqa: BLE001 - report provider-specific failures as blockers
            blockers.append("s3_probe_failed")
            warnings.append(str(exc))

    status: Literal["blocked", "passed", "failed"]
    if blockers:
        status = "blocked" if not probe_attempted else "failed"
    else:
        status = "passed"
        if not require_probe:
            warnings.append("client injected but live probe was not required")

    return S3CompatiblePreflightReport(
        status=status,
        endpoint_url_present=endpoint_url_present,
        bucket_present=bucket_present,
        prefix_present=prefix_present,
        symbolic_credentials_present=symbolic_credentials_present,
        client_injected=client is not None,
        probe_attempted=probe_attempted,
        probe_passed=probe_passed,
        remote_backend_enabled=status == "passed" and client is not None,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def write_s3_compatible_preflight_report(
    path: str | Path,
    report: S3CompatiblePreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_s3_compatible_preflight_report(path: str | Path) -> S3CompatiblePreflightReport:
    return S3CompatiblePreflightReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


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
        key = self._key_for_artifact(artifact_id, digest=digest)
        kwargs: dict[str, Any] = {
            "Bucket": self.config.bucket,
            "Key": key,
            "Body": data,
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
            artifact_id = self._artifact_id_from_key(key)
            total_bytes = int(item.get("Size", head.get("ContentLength", 0)))
            digest = ""
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

    def _key_for_artifact(self, artifact_id: str, *, digest: str) -> str:
        safe_id = artifact_id.strip("/").replace("..", "_")
        versioned_id = f"{safe_id}/{digest}"
        prefix = self._prefix()
        return f"{prefix}/{versioned_id}" if prefix else versioned_id

    def _artifact_id_from_key(self, key: str) -> str:
        prefix = self._prefix()
        relative = key[len(prefix) + 1 :] if prefix and key.startswith(prefix + "/") else key
        parts = relative.rsplit("/", 1)
        return parts[0] if len(parts) == 2 else relative

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
