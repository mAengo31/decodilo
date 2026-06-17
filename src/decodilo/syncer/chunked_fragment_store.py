"""Chunk-aware fragment storage for future large model states."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import MemoryBudgetExceeded
from decodilo.storage.memory_budget import MemoryBudget

StorageKind = Literal["memory", "spill", "chunk_store", "metadata_only"]


@dataclass(frozen=True)
class FragmentPayloadRef:
    storage_kind: StorageKind
    payload_bytes: int
    checksum: str
    content_hash: str | None = None
    manifest_path: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True)
class StoredFragment:
    learner_id: str
    fragment_id: int
    global_version: int
    token_count: int
    payload_ref: FragmentPayloadRef
    idempotency_key: str | None = None
    data: np.ndarray | None = None


@dataclass(frozen=True)
class FragmentStoragePolicy:
    max_in_memory_fragment_bytes: int = 1_000_000
    allow_spill_to_disk: bool = False
    spill_dir: Path | None = None
    max_spill_bytes: int = 0
    chunk_size_bytes: int = 1024 * 1024
    metadata_only_threshold_bytes: int | None = None


@dataclass
class ChunkedFragmentStoreMetrics:
    stored_fragments: int = 0
    duplicate_fragments: int = 0
    memory_budget_rejections: int = 0
    spill_writes: int = 0
    spill_reads: int = 0
    current_in_memory_bytes: int = 0
    peak_in_memory_bytes: int = 0
    current_spill_bytes: int = 0
    peak_spill_bytes: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)


class ChunkedFragmentStore:
    """Stores small fragments in memory and large fragments by reference."""

    def __init__(self, *, policy: FragmentStoragePolicy) -> None:
        self.policy = policy
        spill_dir = policy.spill_dir or Path(".decodilo-spill")
        self.budget = MemoryBudget(
            max_in_memory_fragment_bytes=policy.max_in_memory_fragment_bytes,
            max_total_in_memory_bytes=policy.max_in_memory_fragment_bytes * 4,
            spill_dir=spill_dir,
            allow_spill_to_disk=policy.allow_spill_to_disk,
            max_spill_bytes=policy.max_spill_bytes,
        )
        self.chunk_store = ChunkStore(spill_dir)
        self.fragments: dict[str, StoredFragment] = {}
        self.metrics = ChunkedFragmentStoreMetrics()

    def store_fragment(
        self,
        *,
        learner_id: str,
        fragment_id: int,
        global_version: int,
        token_count: int,
        payload: bytes | np.ndarray | None,
        idempotency_key: str | None = None,
        metadata: dict | None = None,
        declared_payload_bytes: int | None = None,
    ) -> StoredFragment:
        if idempotency_key and idempotency_key in self.fragments:
            self.metrics.duplicate_fragments += 1
            return self.fragments[idempotency_key]
        data_array: np.ndarray | None = None
        if isinstance(payload, np.ndarray):
            data_array = np.asarray(payload, dtype=np.float64).copy()
            payload_bytes = data_array.tobytes()
        else:
            payload_bytes = payload or b""
        size = declared_payload_bytes if payload is None else len(payload_bytes)
        checksum = sha256_bytes(payload_bytes) if payload is not None else str(metadata or {})
        if (
            payload is None
            and self.policy.metadata_only_threshold_bytes is not None
            and size >= self.policy.metadata_only_threshold_bytes
        ):
            stored = StoredFragment(
                learner_id=learner_id,
                fragment_id=fragment_id,
                global_version=global_version,
                token_count=token_count,
                payload_ref=FragmentPayloadRef(
                    storage_kind="metadata_only",
                    payload_bytes=size,
                    checksum=checksum,
                    content_hash=(metadata or {}).get("content_hash"),
                    metadata=metadata or {},
                ),
                idempotency_key=idempotency_key,
            )
            return self._record(idempotency_key, stored)
        if size <= self.policy.max_in_memory_fragment_bytes:
            self.budget.reserve_memory(size)
            self.metrics.current_in_memory_bytes = self.budget.current_in_memory_bytes
            self.metrics.peak_in_memory_bytes = self.budget.peak_in_memory_bytes
            stored = StoredFragment(
                learner_id=learner_id,
                fragment_id=fragment_id,
                global_version=global_version,
                token_count=token_count,
                payload_ref=FragmentPayloadRef(
                    storage_kind="memory",
                    payload_bytes=size,
                    checksum=checksum,
                    metadata=metadata or {},
                ),
                idempotency_key=idempotency_key,
                data=data_array,
            )
            return self._record(idempotency_key, stored)
        if not self.policy.allow_spill_to_disk:
            self._reject("memory_budget")
            raise MemoryBudgetExceeded("fragment exceeds in-memory budget and spill is disabled")
        if not self.budget.can_spill(size):
            self._reject("spill_budget")
            raise MemoryBudgetExceeded("fragment exceeds spill budget")
        self.budget.reserve_spill(size)
        manifest_path = (
            self.chunk_store.manifest_root
            / f"{learner_id}-{fragment_id}-{global_version}-{checksum[:12]}.json"
        )
        manifest = write_binary_artifact(
            store=self.chunk_store,
            data=payload_bytes,
            artifact_id=f"{learner_id}:{fragment_id}:{global_version}:{checksum[:12]}",
            artifact_type="fragment_payload",
            run_id=learner_id,
            chunk_size_bytes=self.policy.chunk_size_bytes,
            metadata=metadata,
            manifest_path=manifest_path,
        )
        self.metrics.spill_writes += 1
        self.metrics.current_spill_bytes = self.budget.current_spill_bytes
        self.metrics.peak_spill_bytes = self.budget.peak_spill_bytes
        stored = StoredFragment(
            learner_id=learner_id,
            fragment_id=fragment_id,
            global_version=global_version,
            token_count=token_count,
            payload_ref=FragmentPayloadRef(
                storage_kind="spill",
                payload_bytes=size,
                checksum=checksum,
                content_hash=manifest.root_hash,
                manifest_path=str(manifest_path),
                metadata=metadata or {},
            ),
            idempotency_key=idempotency_key,
        )
        return self._record(idempotency_key, stored)

    def _record(self, key: str | None, fragment: StoredFragment) -> StoredFragment:
        if key:
            self.fragments[key] = fragment
        self.metrics.stored_fragments += 1
        return fragment

    def _reject(self, reason: str) -> None:
        self.metrics.memory_budget_rejections += 1
        self.metrics.rejection_reasons[reason] = self.metrics.rejection_reasons.get(reason, 0) + 1

    def event_payload(self, fragment: StoredFragment) -> dict:
        return {
            "learner_id": fragment.learner_id,
            "fragment_id": fragment.fragment_id,
            "global_version": fragment.global_version,
            "token_count": fragment.token_count,
            "payload_bytes": fragment.payload_ref.payload_bytes,
            "checksum": fragment.payload_ref.checksum,
            "storage_kind": fragment.payload_ref.storage_kind,
            "content_hash": fragment.payload_ref.content_hash,
        }
