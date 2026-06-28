"""Freshness checks for price snapshots."""

from __future__ import annotations

from datetime import datetime

from decodilo.errors import PricingAmbiguityError
from decodilo.pricing.snapshots import PriceSnapshot
from decodilo.time_compat import UTC


def _parse_timestamp(value: str) -> datetime:
    if value == "unknown":
        raise PricingAmbiguityError("price snapshot captured_at_utc is unknown")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def snapshot_age_days(snapshot: PriceSnapshot, *, now: datetime | None = None) -> float:
    current = now or datetime.now(UTC)
    captured = _parse_timestamp(snapshot.captured_at_utc)
    return (current - captured).total_seconds() / 86_400


def is_stale(
    snapshot: PriceSnapshot,
    *,
    max_age_days: int = 7,
    now: datetime | None = None,
) -> bool:
    return snapshot_age_days(snapshot, now=now) > max_age_days


def require_usable_snapshot(
    snapshot: PriceSnapshot,
    *,
    allow_sample_prices: bool = False,
    allow_stale_prices: bool = False,
    max_price_age_days: int = 7,
    now: datetime | None = None,
) -> None:
    if snapshot.is_sample_data and not allow_sample_prices:
        raise PricingAmbiguityError("sample price snapshot rejected by default")
    if is_stale(snapshot, max_age_days=max_price_age_days, now=now) and not allow_stale_prices:
        raise PricingAmbiguityError("stale price snapshot rejected by default")
