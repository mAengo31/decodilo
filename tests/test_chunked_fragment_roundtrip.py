import numpy as np

from decodilo.syncer.chunked_fragment_store import (
    ChunkedFragmentStore,
    FragmentStoragePolicy,
)


def test_chunked_fragment_small_payload_stored_in_memory(tmp_path) -> None:
    store = ChunkedFragmentStore(
        policy=FragmentStoragePolicy(max_in_memory_fragment_bytes=1024, spill_dir=tmp_path)
    )

    stored = store.store_fragment(
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        token_count=10,
        payload=np.asarray([1.0, 2.0]),
        idempotency_key="k",
    )

    assert stored.payload_ref.storage_kind == "memory"
    assert stored.data is not None
    assert store.event_payload(stored)["payload_bytes"] > 0


def test_chunked_fragment_large_payload_spills_and_deduplicates(tmp_path) -> None:
    store = ChunkedFragmentStore(
        policy=FragmentStoragePolicy(
            max_in_memory_fragment_bytes=4,
            allow_spill_to_disk=True,
            spill_dir=tmp_path,
            max_spill_bytes=100,
            chunk_size_bytes=4,
        )
    )

    first = store.store_fragment(
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        token_count=10,
        payload=b"large-payload",
        idempotency_key="k",
    )
    second = store.store_fragment(
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        token_count=10,
        payload=b"large-payload",
        idempotency_key="k",
    )

    assert first is second
    assert first.payload_ref.storage_kind == "spill"
    assert store.metrics.duplicate_fragments == 1

