"""Deterministic local fault injection for artifact backends."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from decodilo.storage.artifact_backend import (
    ArtifactBackend,
    ArtifactBackendCapabilities,
    ArtifactBackendRef,
)
from decodilo.storage.backend_metrics import BackendMetrics
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.retry_policy import RetryPolicy, run_with_retries


class InjectedBackendFailure(OSError):
    """Raised for deterministic transient or permanent backend failures."""


class InjectedBackendCorruption(RuntimeError):
    """Raised when injected corruption is detected by checksum validation."""


@dataclass
class FaultInjectionConfig:
    seed: int = 0
    transient_read_failures: int = 0
    transient_write_failures: int = 0
    permanent_read_failure: bool = False
    corrupt_reads: int = 0
    slow_read_seconds: float = 0.0
    slow_write_seconds: float = 0.0
    partial_write_failure: bool = False


class FaultInjectedArtifactBackend:
    """Wrap an artifact backend with deterministic local-only failures."""

    def __init__(
        self,
        backend: ArtifactBackend,
        *,
        config: FaultInjectionConfig | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.backend = backend
        self.config = config or FaultInjectionConfig()
        self.retry_policy = retry_policy or RetryPolicy()
        self.metrics = BackendMetrics()
        self._rng = random.Random(self.config.seed)
        self._read_failures_remaining = self.config.transient_read_failures
        self._write_failures_remaining = self.config.transient_write_failures
        self._corrupt_reads_remaining = self.config.corrupt_reads

    def capabilities(self) -> ArtifactBackendCapabilities:
        return self.backend.capabilities()

    def write_bytes(self, *, artifact_id: str, data: bytes) -> ArtifactBackendRef:
        def op() -> ArtifactBackendRef:
            if self.config.slow_write_seconds:
                time.sleep(self.config.slow_write_seconds)
            if self.config.partial_write_failure:
                raise InjectedBackendFailure("injected partial write failure before commit")
            if self._write_failures_remaining > 0:
                self._write_failures_remaining -= 1
                raise InjectedBackendFailure("injected transient write failure")
            ref = self.backend.write_bytes(artifact_id=artifact_id, data=data)
            self.metrics.backend_writes += 1
            self.metrics.backend_bytes_written += len(data)
            return ref

        return run_with_retries(op, policy=self.retry_policy, metrics=self.metrics)

    def read_bytes(self, ref: ArtifactBackendRef) -> bytes:
        expected_hash = ref.metadata.get("sha256")

        def op() -> bytes:
            if self.config.slow_read_seconds:
                time.sleep(self.config.slow_read_seconds)
            if self.config.permanent_read_failure:
                raise InjectedBackendFailure("injected permanent read failure")
            if self._read_failures_remaining > 0:
                self._read_failures_remaining -= 1
                raise InjectedBackendFailure("injected transient read failure")
            data = self.backend.read_bytes(ref)
            if self._corrupt_reads_remaining > 0:
                self._corrupt_reads_remaining -= 1
                data = _corrupt(data, self._rng)
            if expected_hash is not None and sha256_bytes(data) != expected_hash:
                self.metrics.backend_corruptions_detected += 1
                raise InjectedBackendCorruption("injected corrupted read detected")
            self.metrics.backend_reads += 1
            self.metrics.backend_bytes_read += len(data)
            return data

        return run_with_retries(op, policy=self.retry_policy, metrics=self.metrics)

    def list_refs(self) -> list[ArtifactBackendRef]:
        return self.backend.list_refs()


def _corrupt(data: bytes, rng: random.Random) -> bytes:
    if not data:
        return b"x"
    mutable = bytearray(data)
    index = rng.randrange(len(mutable))
    mutable[index] ^= 1
    return bytes(mutable)
