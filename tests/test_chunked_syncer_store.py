import pytest

from decodilo.storage.errors import MemoryBudgetExceeded
from decodilo.syncer.chunked_fragment_store import (
    ChunkedFragmentStore,
    FragmentStoragePolicy,
)
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.trainer.synthetic_large_state import SyntheticLargeStateSource


def test_over_budget_chunked_fragment_is_rejected(tmp_path) -> None:
    store = ChunkedFragmentStore(
        policy=FragmentStoragePolicy(
            max_in_memory_fragment_bytes=4,
            allow_spill_to_disk=False,
            spill_dir=tmp_path,
        )
    )

    with pytest.raises(MemoryBudgetExceeded):
        store.store_fragment(
            learner_id="learner-0",
            fragment_id=0,
            global_version=0,
            token_count=10,
            payload=b"large-payload",
        )

    assert store.metrics.memory_budget_rejections == 1
    assert store.metrics.rejection_reasons["memory_budget"] == 1


def test_metadata_only_large_fragment_does_not_embed_payload(tmp_path) -> None:
    store = ChunkedFragmentStore(
        policy=FragmentStoragePolicy(
            max_in_memory_fragment_bytes=4,
            spill_dir=tmp_path,
            metadata_only_threshold_bytes=1024,
        )
    )

    stored = store.store_fragment(
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        token_count=10,
        payload=None,
        declared_payload_bytes=10_000,
        metadata={"synthetic": True, "lineage": "abc"},
    )

    event_payload = store.event_payload(stored)
    assert event_payload["storage_kind"] == "metadata_only"
    assert "data" not in event_payload


def test_metadata_only_large_fragment_event_log_stays_small(tmp_path) -> None:
    source = SyntheticLargeStateSource(
        run_id="run-large",
        learner_id="learner-0",
        seed=123,
        logical_parameter_count=512 * 1024 * 1024,
        bytes_per_parameter=2,
    )
    manifest = source.manifest()
    store = ChunkedFragmentStore(
        policy=FragmentStoragePolicy(
            max_in_memory_fragment_bytes=1024,
            spill_dir=tmp_path,
            metadata_only_threshold_bytes=1024,
        )
    )
    stored = store.store_fragment(
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        token_count=10,
        payload=None,
        declared_payload_bytes=manifest.total_logical_bytes,
        metadata={
            "synthetic": True,
            "manifest_hash": manifest.manifest_hash,
            "content_hash": manifest.manifest_hash,
        },
    )
    event_payload = store.event_payload(stored)
    event_log_path = tmp_path / "events.jsonl"
    EventLog(event_log_path, run_id="run-large").append(
        EventType.LEARNER_FRAGMENT_SUBMITTED,
        logical_time=0,
        learner_id="learner-0",
        payload=event_payload,
    )
    text = event_log_path.read_text(encoding="utf-8")

    assert manifest.total_logical_bytes >= 1024 * 1024 * 1024
    assert event_log_path.stat().st_size <= 5 * 1024 * 1024
    assert "payload_bytes" in text
    assert "checksum" in text
    assert "storage_kind" in text
    assert "metadata_only" in text
    assert "content_hash" in text
    assert event_payload["content_hash"] == manifest.manifest_hash
    assert "data" not in event_payload
    assert "vector" not in text
