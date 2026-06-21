"""Validation for non-sample Lambda price snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.pricing.freshness import snapshot_age_days
from decodilo.pricing.snapshots import PriceSnapshot, load_price_snapshot


class LambdaNonSamplePriceSnapshotReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    price_snapshot_id: str
    is_sample_data: bool
    source_url_present: bool
    source_hash_present: bool
    captured_at_present: bool
    snapshot_age_days: float | None
    max_age_days: float = 7.0
    non_sample_price_snapshot_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_non_sample_price_snapshot(
    snapshot: PriceSnapshot,
    *,
    max_age_days: float = 7.0,
    allow_stale: bool = False,
) -> LambdaNonSamplePriceSnapshotReport:
    blockers: list[str] = []
    warnings: list[str] = []
    age = None
    if snapshot.is_sample_data:
        blockers.append("price snapshot is sample data")
    if not snapshot.source_url:
        blockers.append("price snapshot missing source_url")
    if not snapshot.source_sha256:
        blockers.append("price snapshot missing source hash")
    if not snapshot.captured_at_utc:
        blockers.append("price snapshot missing captured_at_utc")
    try:
        age = snapshot_age_days(snapshot)
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"price snapshot age unavailable: {exc}")
    if age is not None and age > max_age_days:
        message = f"price snapshot is stale: {age:.1f} days old"
        if allow_stale:
            warnings.append(message)
        else:
            blockers.append(message)
    return LambdaNonSamplePriceSnapshotReport(
        price_snapshot_id=snapshot.snapshot_id,
        is_sample_data=snapshot.is_sample_data,
        source_url_present=bool(snapshot.source_url),
        source_hash_present=bool(snapshot.source_sha256),
        captured_at_present=bool(snapshot.captured_at_utc),
        snapshot_age_days=age,
        max_age_days=max_age_days,
        non_sample_price_snapshot_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def validate_non_sample_price_snapshot_from_path(
    path: str | Path,
    *,
    max_age_days: float = 7.0,
    allow_stale: bool = False,
) -> LambdaNonSamplePriceSnapshotReport:
    return validate_non_sample_price_snapshot(
        load_price_snapshot(path),
        max_age_days=max_age_days,
        allow_stale=allow_stale,
    )
