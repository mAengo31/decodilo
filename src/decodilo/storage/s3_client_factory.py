"""Explicit S3-compatible client factory boundary.

This module is intentionally dependency-free. It never imports cloud SDKs,
reads environment variables, or creates clients implicitly. Runtime callers must
supply either an already-constructed client or a factory callable that receives a
safe, symbolic ``S3CompatibleBackendConfig`` and returns a client.
"""

from __future__ import annotations

from collections.abc import Callable

from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
    S3CompatibleBackendNotConfigured,
    S3CompatibleClient,
    preflight_s3_compatible_backend,
)

S3CompatibleClientFactory = Callable[[S3CompatibleBackendConfig], S3CompatibleClient]


def create_s3_compatible_backend(
    *,
    config: S3CompatibleBackendConfig | None,
    client: S3CompatibleClient | None = None,
    client_factory: S3CompatibleClientFactory | None = None,
    require_probe: bool = False,
) -> S3CompatibleArtifactBackend:
    """Create an S3-compatible backend only from explicit injection.

    The fail-closed behavior is deliberate: no dependency discovery, no secret
    lookup, and no network-capable client construction happen here. If
    ``require_probe`` is true the injected client is probed through the existing
    preflight path before returning the backend.
    """

    if config is None:
        raise S3CompatibleBackendNotConfigured("S3-compatible backend config is required")
    resolved_client = client
    if resolved_client is None and client_factory is not None:
        resolved_client = client_factory(config)
    if resolved_client is None:
        raise S3CompatibleBackendNotConfigured(
            "S3-compatible backend requires an explicitly injected client or client factory"
        )
    report = preflight_s3_compatible_backend(
        config,
        client=resolved_client,
        require_probe=require_probe,
    )
    if report.status != "passed":
        blocker_text = ", ".join(report.blockers) or report.status
        raise S3CompatibleBackendNotConfigured(
            f"S3-compatible backend preflight did not pass: {blocker_text}"
        )
    return S3CompatibleArtifactBackend(config, client=resolved_client)
