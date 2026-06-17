import pytest

from decodilo.syncer.idempotency_compaction import (
    IdempotencyCompactionPolicy,
    compact_idempotency_store,
)
from decodilo.syncer.idempotency_store import IdempotencyRecord, IdempotencyStore

pytestmark = pytest.mark.unit


def _record(key: str, version: int, logical_time: int) -> IdempotencyRecord:
    return IdempotencyRecord(
        run_id="run-compact",
        idempotency_key=key,
        learner_id="learner-0",
        fragment_id=key,
        first_seen_global_version=version,
        last_seen_global_version=version,
        decision="accepted",
        token_count=1,
        useful_tokens_counted=True,
        created_logical_time=logical_time,
        last_seen_logical_time=logical_time,
    )


def test_compaction_preserves_needed_duplicate_suppression() -> None:
    store = IdempotencyStore(run_id="run-compact")
    for index in range(5):
        store = store.put(_record(f"k{index}", index, index))

    compacted, report = compact_idempotency_store(
        store,
        IdempotencyCompactionPolicy(
            global_version_watermark=1,
            logical_time_watermark=1,
            retain_latest_global_versions=2,
        ),
        current_global_version=4,
        in_flight_keys={"k0"},
    )

    assert "k0" in compacted.records
    assert "k1" not in compacted.records
    assert compacted.duplicate_decision("k1", logical_time=10, global_version=5).decision == (
        "expired_duplicate"
    )
    assert report.records_compacted == 1
    assert report.protected_records >= 1


def test_compaction_does_not_remove_in_flight_records() -> None:
    store = IdempotencyStore(run_id="run-compact").put(_record("old", 0, 0))

    compacted, report = compact_idempotency_store(
        store,
        IdempotencyCompactionPolicy(global_version_watermark=10, logical_time_watermark=10),
        current_global_version=10,
        in_flight_keys={"old"},
    )

    assert "old" in compacted.records
    assert report.records_compacted == 0

