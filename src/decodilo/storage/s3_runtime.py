"""Runtime S3-compatible client construction for explicit subprocess use.

Unlike ``s3_compatible_backend.py`` this module is allowed to resolve symbolic
credential references from an explicitly supplied environment mapping. It still
fails closed: no defaults are inferred unless the caller requested the symbolic
ref names, and boto3 is imported only inside the constructor.
"""

from __future__ import annotations

from collections.abc import Mapping

from decodilo.errors import InvariantViolation
from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
    S3CompatibleBackendNotConfigured,
    preflight_s3_compatible_backend,
)


def create_boto3_s3_compatible_backend_from_env(
    config: S3CompatibleBackendConfig,
    *,
    environ: Mapping[str, str],
    require_probe: bool = False,
) -> S3CompatibleArtifactBackend:
    """Build an S3-compatible backend from explicit env-var references."""

    access_key = _resolve_env_ref(config.access_key_ref, environ, "access_key_ref")
    secret_key = _resolve_env_ref(config.secret_key_ref, environ, "secret_key_ref")
    session_token = (
        _resolve_env_ref(config.session_token_ref, environ, "session_token_ref")
        if config.session_token_ref
        else None
    )
    try:
        import boto3  # type: ignore[import-not-found]
        from botocore.config import Config  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - optional runtime dependency
        raise S3CompatibleBackendNotConfigured(
            "boto3/botocore are required for subprocess S3-compatible runtime"
        ) from exc

    client_kwargs = {
        "endpoint_url": config.endpoint_url,
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region_name": config.region or "us-east-1",
        "config": Config(signature_version="s3v4"),
    }
    if session_token is not None:
        client_kwargs["aws_session_token"] = session_token
    client = boto3.client("s3", **client_kwargs)
    report = preflight_s3_compatible_backend(
        config,
        client=client,
        require_probe=require_probe,
    )
    if report.status != "passed":
        raise S3CompatibleBackendNotConfigured(
            "S3-compatible runtime preflight failed: " + ",".join(report.blockers)
        )
    return S3CompatibleArtifactBackend(config, client=client)


def _resolve_env_ref(ref: str | None, environ: Mapping[str, str], label: str) -> str:
    if not ref:
        raise S3CompatibleBackendNotConfigured(f"missing S3 {label}")
    if ref not in environ or not environ[ref]:
        raise S3CompatibleBackendNotConfigured(f"S3 env ref {ref!r} is not set")
    value = environ[ref]
    if "\n" in value or "\x00" in value:
        raise InvariantViolation(f"S3 env ref {ref!r} contains invalid characters")
    return value


def artifact_transport_for_s3_ref(
    *,
    workdir,
    artifact_root,
    ref: dict,
    environ: Mapping[str, str],
):
    """Build a LocalArtifactTransport capable of reading an S3-compatible ref."""

    from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport

    s3_backend = None
    if ref.get("storage_backend") == "s3_compatible":
        metadata = ref.get("metadata") or {}
        manifest_ref = metadata.get("s3_compatible_manifest_ref") or {}
        manifest_metadata = (
            manifest_ref.get("metadata") if isinstance(manifest_ref, dict) else {}
        ) or {}
        endpoint_url = str(manifest_metadata.get("endpoint_url") or "")
        bucket = str(manifest_metadata.get("bucket") or "")
        if endpoint_url and bucket:
            s3_backend = create_boto3_s3_compatible_backend_from_env(
                S3CompatibleBackendConfig(
                    endpoint_url=endpoint_url,
                    bucket=bucket,
                    prefix="",
                    region=environ.get("AWS_REGION"),
                    access_key_ref="AWS_ACCESS_KEY_ID",
                    secret_key_ref="AWS_SECRET_ACCESS_KEY",
                ),
                environ=environ,
                require_probe=False,
            )
    return LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(workdir),
            artifact_root=str(artifact_root),
            storage_backend=str(ref.get("storage_backend") or "local_filesystem"),
        ),
        s3_backend=s3_backend,
    )
