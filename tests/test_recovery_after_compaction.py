import pytest

from decodilo.syncer.idempotency_compaction import (
    IdempotencyCompactionPolicy,
    compact_idempotency_store,
)
from decodilo.syncer.idempotency_store import IdempotencyRecord, IdempotencyStore

pytestmark = [pytest.mark.lifecycle, pytest.mark.replay]


def test_duplicate_before_compaction_watermark_is_expired_duplicate() -> None:
    record = IdempotencyRecord(
        run_id="run-recovery-compact",
        idempotency_key="old-key",
        learner_id="learner-0",
        fragment_id="fragment-0",
        first_seen_global_version=1,
        last_seen_global_version=1,
        decision="accepted",
        token_count=10,
        useful_tokens_counted=True,
        created_logical_time=1,
        last_seen_logical_time=1,
    )
    store = IdempotencyStore(run_id="run-recovery-compact").put(record)

    compacted, _ = compact_idempotency_store(
        store,
        IdempotencyCompactionPolicy(global_version_watermark=2, logical_time_watermark=2),
        current_global_version=10,
    )

    duplicate = compacted.duplicate_decision("old-key", logical_time=100, global_version=10)
    assert duplicate.decision == "expired_duplicate"

