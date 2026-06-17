"""Helpers for deriving local runtime overhead metrics."""

from __future__ import annotations


def safe_fraction(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(float(value) / float(total), 1.0))


def useful_tokens_per_second(tokens: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return max(float(tokens), 0.0) / seconds
