"""Helpers for identifying local runtime bottlenecks from measured counters."""

from __future__ import annotations

from typing import Any


def top_components_by_value(
    values: dict[str, float | int | None],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return a stable descending ranking, ignoring missing values."""

    normalized = [
        {"component": key, "value": float(value)}
        for key, value in values.items()
        if value is not None
    ]
    normalized.sort(key=lambda item: (-item["value"], item["component"]))
    return normalized[:limit]


def bounded_fraction(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, float(numerator) / float(denominator)))
