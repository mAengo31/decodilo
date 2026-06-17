"""Safe compaction policies for the syncer idempotency table."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from decodilo.syncer.idempotency_store import IdempotencyStore


class IdempotencyCompactionPolicy(BaseModel):
    """Watermarks and retention windows for idempotency compaction."""

    model_config = ConfigDict(frozen=True)

    global_version_watermark: int | None = Field(default=None, ge=0)
    logical_time_watermark: int | None = Field(default=None, ge=0)
    max_records: int | None = Field(default=None, gt=0)
    retain_latest_global_versions: int = Field(default=2, ge=0)
    duplicate_suppression_window_versions: int = Field(default=2, ge=0)


class IdempotencyCompactionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    records_before: int
    records_after: int
    records_compacted: int
    compacted_through_global_version: int
    compacted_through_logical_time: int
    protected_records: int
    warnings: list[str] = Field(default_factory=list)


def compact_idempotency_store(
    store: IdempotencyStore,
    policy: IdempotencyCompactionPolicy,
    *,
    current_global_version: int,
    in_flight_keys: Iterable[str] = (),
) -> tuple[IdempotencyStore, IdempotencyCompactionReport]:
    """Compact old records into tombstones while preserving duplicate suppression."""

    in_flight = set(in_flight_keys)
    protected_min_version = max(
        0,
        current_global_version
        - max(policy.retain_latest_global_versions, policy.duplicate_suppression_window_versions),
    )
    candidates: list[str] = []
    protected = 0
    warnings: list[str] = []
    for key, record in store.records.items():
        if key in in_flight:
            protected += 1
            continue
        if record.last_seen_global_version >= protected_min_version:
            protected += 1
            continue
        if (
            policy.global_version_watermark is not None
            and record.last_seen_global_version > policy.global_version_watermark
        ):
            protected += 1
            continue
        if (
            policy.logical_time_watermark is not None
            and record.last_seen_logical_time > policy.logical_time_watermark
        ):
            protected += 1
            continue
        candidates.append(key)

    compacted = store
    if policy.max_records is not None:
        overflow = max(0, len(store.records) - policy.max_records)
        if overflow > 0:
            ordered = sorted(
                (
                    (record.last_seen_logical_time, key)
                    for key, record in store.records.items()
                    if key not in in_flight
                    and store.records[key].last_seen_global_version < protected_min_version
                )
            )
            for _, key in ordered[:overflow]:
                if key not in candidates:
                    candidates.append(key)
        elif not candidates:
            warnings.append("max_records did not require compaction")

    for key in candidates:
        compacted = compacted.expire(key)

    compacted = compacted.model_copy(
        update={
            "compacted_through_global_version": max(
                compacted.compacted_through_global_version,
                policy.global_version_watermark or 0,
            ),
            "compacted_through_logical_time": max(
                compacted.compacted_through_logical_time,
                policy.logical_time_watermark or 0,
            ),
        }
    )
    report = IdempotencyCompactionReport(
        records_before=len(store.records),
        records_after=len(compacted.records),
        records_compacted=len(store.records) - len(compacted.records),
        compacted_through_global_version=compacted.compacted_through_global_version,
        compacted_through_logical_time=compacted.compacted_through_logical_time,
        protected_records=protected,
        warnings=warnings,
    )
    return compacted, report

