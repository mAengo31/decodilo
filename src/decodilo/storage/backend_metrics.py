"""Metrics for artifact backend operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackendMetrics:
    backend_reads: int = 0
    backend_writes: int = 0
    backend_retries: int = 0
    backend_failures: int = 0
    backend_corruptions_detected: int = 0
    backend_bytes_read: int = 0
    backend_bytes_written: int = 0
