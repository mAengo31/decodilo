import pytest

from decodilo.syncer.idempotency_compaction import (
    IdempotencyCompactionPolicy,
    compact_idempotency_store,
)
from decodilo.syncer.idempotency_store import IdempotencyRecord, IdempotencyStore

pytestmark = [pytest.mark.lifecycle, pytest.mark.unit]


def test_synthetic_10k_record_compaction_is_deterministic_and_bounded() -> None:
    store = IdempotencyStore(run_id="run-idem-stress")
    for index in range(10_000):
        store = store.put(
            IdempotencyRecord(
                run_id="run-idem-stress",
                idempotency_key=f"k-{index}",
                learner_id=f"learner-{index % 4}",
                fragment_id=f"fragment-{index}",
                first_seen_global_version=index % 100,
                last_seen_global_version=index % 100,
                decision="accepted" if index % 3 else "rejected",
                rejection_reason="stale" if index % 3 == 0 else None,
                token_count=index % 17,
                useful_tokens_counted=index % 3 != 0,
                created_logical_time=index,
                last_seen_logical_time=index,
            )
        )

    compacted, report = compact_idempotency_store(
        store,
        IdempotencyCompactionPolicy(
            global_version_watermark=50,
            logical_time_watermark=9000,
            max_records=2000,
            retain_latest_global_versions=5,
        ),
        current_global_version=99,
        in_flight_keys={"k-1"},
    )

    assert report.records_after < report.records_before
    assert "k-1" in compacted.records
    duplicate = compacted.duplicate_decision(
        "k-0",
        logical_time=20_000,
        global_version=100,
    )
    assert duplicate.decision in {
        "expired_duplicate",
        "duplicate",
    }
    restored = IdempotencyStore.from_checkpoint_payload(compacted.to_checkpoint_payload())
    assert restored.compacted_through_global_version == compacted.compacted_through_global_version
