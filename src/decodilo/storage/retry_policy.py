"""Small deterministic retry helper for artifact backend tests."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from decodilo.storage.backend_metrics import BackendMetrics

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retryable_error_types: tuple[type[BaseException], ...] = (OSError,)
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be non-negative")


def run_with_retries(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy,
    metrics: BackendMetrics | None = None,
) -> T:
    attempts = 0
    while True:
        attempts += 1
        try:
            return operation()
        except policy.retryable_error_types:
            if metrics is not None:
                metrics.backend_failures += 1
            if attempts >= policy.max_attempts:
                raise
            if metrics is not None:
                metrics.backend_retries += 1
            if policy.backoff_seconds:
                time.sleep(policy.backoff_seconds)
