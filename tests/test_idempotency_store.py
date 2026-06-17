import pytest

from decodilo.syncer.idempotency_store import IdempotencyRecord, IdempotencyStore

pytestmark = pytest.mark.unit


def _record(key: str, *, version: int = 1, decision: str = "accepted") -> IdempotencyRecord:
    return IdempotencyRecord(
        run_id="run-idem",
        idempotency_key=key,
        learner_id="learner-0",
        fragment_id="fragment-0",
        first_seen_global_version=version,
        last_seen_global_version=version,
        decision=decision,
        token_count=10,
        useful_tokens_counted=decision == "accepted",
        created_logical_time=version,
        last_seen_logical_time=version,
    )


def test_duplicate_accepted_fragment_not_double_applied() -> None:
    store = IdempotencyStore(run_id="run-idem").put(_record("k1"))

    duplicate = store.duplicate_decision("k1", logical_time=5, global_version=2)

    assert duplicate.decision == "duplicate"
    assert duplicate.token_count == 10
    assert duplicate.useful_tokens_counted is True
    assert store.record_count == 1


def test_duplicate_rejected_fragment_remains_rejected() -> None:
    store = IdempotencyStore(run_id="run-idem").put(
        _record("k1", decision="rejected").model_copy(
            update={"rejection_reason": "stale", "useful_tokens_counted": False}
        )
    )

    duplicate = store.duplicate_decision("k1", logical_time=5, global_version=2)

    assert duplicate.decision == "duplicate"
    assert duplicate.rejection_reason == "stale"
    assert duplicate.useful_tokens_counted is False


def test_idempotency_store_checkpoint_roundtrip() -> None:
    store = IdempotencyStore(run_id="run-idem").put(_record("k1"))

    restored = IdempotencyStore.from_checkpoint_payload(store.to_checkpoint_payload())

    assert restored == store
    assert (
        restored.duplicate_decision("k1", logical_time=9, global_version=3).decision
        == "duplicate"
    )
