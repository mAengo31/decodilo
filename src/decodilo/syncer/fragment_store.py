"""Fragment store and syncer state for asynchronous learner updates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from decodilo.errors import InvariantViolation
from decodilo.protocol.messages import CheckpointRecord, MergeDecision
from decodilo.sim.fake_model import split_vector
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.outer_optimizer import OuterOptimizer, SGDOuterOptimizer, outer_optimizer_name
from decodilo.syncer.quorum import PendingUpdate, QuorumPolicy, QuorumTracker
from decodilo.syncer.streaming_merge import streaming_token_weighted_merge
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge


@dataclass(frozen=True)
class SubmittedLearnerUpdate(PendingUpdate):
    """A full learner vector plus metadata needed by the syncer."""

    vector: NDArray[np.float64]


@dataclass
class SyncerMetrics:
    """Counters emitted by the syncer."""

    accepted_updates: int = 0
    rejected_updates: int = 0
    useful_tokens: int = 0
    rejected_tokens: int = 0
    stale_tokens: int = 0
    sync_rounds_committed: int = 0
    sync_rounds_skipped: int = 0
    rejected_fragments: int = 0
    stale_fragments: int = 0
    chunked_fragment_submissions: int = 0
    inline_fragment_submissions: int = 0
    artifact_ref_validations: int = 0
    artifact_ref_validation_failures: int = 0
    chunked_fragment_bytes_accepted: int = 0
    chunked_fragment_bytes_rejected: int = 0
    artifact_bytes_read: int = 0
    artifact_chunks_read: int = 0
    artifact_validation_seconds: float = 0.0
    live_streaming_merges: int = 0
    live_streaming_merge_bytes_read: int = 0
    live_streaming_merge_bytes_written: int = 0
    live_streaming_merge_chunks_processed: int = 0
    live_streaming_merge_peak_working_bytes_estimate: int = 0
    binary_streaming_merges: int = 0
    binary_streaming_merge_bytes_read: int = 0
    binary_streaming_merge_bytes_written: int = 0
    binary_streaming_merge_chunks_read: int = 0
    binary_streaming_merge_chunks_written: int = 0
    binary_streaming_merge_peak_working_bytes_estimate: int = 0
    binary_streaming_merge_wall_time_seconds: float = 0.0
    numeric_merge_performed: bool = True
    simulation_only_merge_count: int = 0
    quorum_compositions: list[list[str]] = field(default_factory=list)
    rejection_reasons: dict[str, int] = field(default_factory=dict)

    def record_rejection(self, reason: str, tokens: int) -> None:
        self.rejected_updates += 1
        self.rejected_fragments += 1
        self.rejected_tokens += max(tokens, 0)
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
        if reason == "stale":
            self.stale_fragments += 1
            self.stale_tokens += max(tokens, 0)


class FragmentStore:
    """Owns the global vector, pending learner updates, and sync decisions."""

    def __init__(
        self,
        *,
        initial_global_vector: NDArray[np.float64],
        num_fragments: int,
        quorum_policy: QuorumPolicy,
        optimizer: OuterOptimizer | None = None,
        event_log: EventLog | None = None,
        event_payload_mode: str = "inline",
        merge_mode: str = "in_memory",
        global_vector_artifact_writer: Callable[[str, NDArray[np.float64], int], dict[str, Any]]
        | None = None,
        binary_merge_runner: Callable[
            [NDArray[np.float64], dict[str, dict[str, Any]], dict[str, int], float, int],
            Any,
        ]
        | None = None,
    ) -> None:
        self.global_vector = np.asarray(initial_global_vector, dtype=np.float64).copy()
        if self.global_vector.ndim != 1 or self.global_vector.size == 0:
            raise ValueError("initial_global_vector must be a non-empty 1D vector")
        if num_fragments <= 0:
            raise ValueError("num_fragments must be positive")

        self.num_fragments = num_fragments
        self.quorum_policy = quorum_policy
        self.global_version = 0
        self.optimizer = optimizer or SGDOuterOptimizer()
        self.event_log = event_log or EventLog()
        self.event_payload_mode = event_payload_mode
        self.merge_mode = merge_mode
        self.global_vector_artifact_writer = global_vector_artifact_writer
        self.binary_merge_runner = binary_merge_runner
        self.metrics = SyncerMetrics()
        self.pending: dict[str, SubmittedLearnerUpdate] = {}
        self.pending_artifact_refs: dict[str, dict[str, Any]] = {}
        self.tracker = QuorumTracker(quorum_policy)

    def submit_learner_update(
        self,
        *,
        learner_id: str,
        vector: NDArray[np.float64],
        global_version_seen: int,
        tokens: int,
        submitted_at: int,
        artifact_ref: dict[str, Any] | None = None,
        payload_metadata: dict[str, Any] | None = None,
    ) -> None:
        learner_vector = np.asarray(vector, dtype=np.float64).copy()
        if learner_vector.shape != self.global_vector.shape:
            raise ValueError("learner vector shape must match global vector shape")
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        if global_version_seen > self.global_version:
            raise InvariantViolation("learner update cannot reference a future global version")

        update = SubmittedLearnerUpdate(
            learner_id=learner_id,
            global_version_seen=global_version_seen,
            tokens=tokens,
            submitted_at=submitted_at,
            vector=learner_vector,
        )
        self.pending[learner_id] = update
        if artifact_ref is not None:
            self.pending_artifact_refs[learner_id] = artifact_ref
            self.metrics.chunked_fragment_submissions += 1
        else:
            self.metrics.inline_fragment_submissions += 1
        if self.event_payload_mode == "chunked" and artifact_ref is not None:
            payload = {
                "learner_id": learner_id,
                "global_version_seen": global_version_seen,
                "tokens": tokens,
                "storage_kind": "artifact_ref",
                "artifact_ref": artifact_ref,
                "payload_bytes": artifact_ref.get("total_bytes"),
                "manifest_hash": artifact_ref.get("manifest_hash"),
                "content_hash": artifact_ref.get("content_root_hash"),
                "checksum": (payload_metadata or {}).get("checksum"),
                "dtype": (payload_metadata or {}).get("dtype"),
                "shape": (payload_metadata or {}).get("shape"),
            }
        else:
            fragments = split_vector(
                learner_vector,
                num_fragments=self.num_fragments,
                global_version=global_version_seen,
                source_learner_id=learner_id,
                tokens_since_last_sync=tokens,
                created_at=submitted_at,
            )
            payload = {
                "learner_id": learner_id,
                "global_version_seen": global_version_seen,
                "tokens": tokens,
                "vector": learner_vector.tolist(),
                "fragments": [fragment.model_dump(mode="json") for fragment in fragments],
            }
        self.event_log.append(
            EventType.LEARNER_FRAGMENT_SUBMITTED,
            logical_time=submitted_at,
            learner_id=learner_id,
            payload=payload,
        )

    def maybe_commit(
        self,
        *,
        current_tick: int,
        failed_learner_ids: set[str] | None = None,
    ) -> MergeDecision | None:
        decision = self.tracker.decide(
            list(self.pending.values()),
            current_version=self.global_version,
            current_tick=current_tick,
            failed_learner_ids=failed_learner_ids,
        )

        for learner_id, reason in sorted(decision.rejected_learner_ids.items()):
            update = self.pending.pop(learner_id, None)
            self.pending_artifact_refs.pop(learner_id, None)
            tokens = update.tokens if update is not None else 0
            self.metrics.record_rejection(reason, tokens)
            self.event_log.append(
                EventType.FRAGMENT_REJECTED,
                logical_time=current_tick,
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "reason": reason,
                    "tokens": tokens,
                    "global_version": self.global_version,
                },
            )

        if not decision.should_commit:
            if self.pending and decision.reason in {"below_quorum", "partial_round_allowed"}:
                self.metrics.sync_rounds_skipped += 1
                self.event_log.append(
                    EventType.SYNC_ROUND_SKIPPED,
                    logical_time=current_tick,
                    round_id=decision.round_id,
                    payload={
                        "reason": decision.reason,
                        "global_version": self.global_version,
                        "eligible_learner_ids": decision.accepted_learner_ids,
                        "pending_learner_ids": sorted(self.pending),
                    },
                )
            return None

        accepted_updates = [
            self.pending[learner_id]
            for learner_id in decision.accepted_learner_ids
            if learner_id in self.pending
        ]
        if not accepted_updates:
            self.metrics.sync_rounds_skipped += 1
            self.event_log.append(
                EventType.SYNC_ROUND_SKIPPED,
                logical_time=current_tick,
                round_id=decision.round_id,
                payload={"reason": "no_accepted_updates", "global_version": self.global_version},
            )
            self.tracker.reset()
            return None

        if (
            decision.reason != "partial_round_allowed"
            and len(accepted_updates) < self.quorum_policy.min_quorum
        ):
            raise InvariantViolation("sync round cannot commit below quorum")

        round_id = decision.round_id or f"round-{self.global_version + 1:08d}"
        optimizer_name = outer_optimizer_name(self.optimizer)
        outer_momentum = getattr(self.optimizer, "momentum", None)
        self.event_log.append(
            EventType.SYNC_ROUND_STARTED,
            logical_time=current_tick,
            round_id=round_id,
            payload={
                "round_id": round_id,
                "previous_global_version": self.global_version,
                "accepted_learner_ids": [update.learner_id for update in accepted_updates],
                "reason": decision.reason,
            },
        )

        learner_deltas = [
            LearnerDelta(
                learner_id=update.learner_id,
                vector=update.vector,
                tokens=update.tokens,
                global_version_seen=update.global_version_seen,
            )
            for update in accepted_updates
        ]
        if self.merge_mode == "streaming_chunked":
            token_counts = {delta.learner_id: delta.tokens for delta in learner_deltas}
            accepted_artifact_refs = {
                update.learner_id: self.pending_artifact_refs[update.learner_id]
                for update in accepted_updates
                if update.learner_id in self.pending_artifact_refs
            }
            merge_result = token_weighted_merge(
                self.global_vector,
                learner_deltas,
                optimizer=self.optimizer,
            )
            binary_refs = {
                learner_id: ref
                for learner_id, ref in accepted_artifact_refs.items()
                if isinstance(ref, dict)
                and ref.get("metadata", {}).get("codec") == "tensor_binary_v1"
            }
            if binary_refs and self.binary_merge_runner is not None:
                streaming = self.binary_merge_runner(
                    self.global_vector,
                    binary_refs,
                    token_counts,
                    float(getattr(self.optimizer, "outer_lr", 1.0)),
                    max(1, min(1024, self.global_vector.size)),
                )
            else:
                streaming = streaming_token_weighted_merge(
                    global_values=self.global_vector,
                    learner_values={delta.learner_id: delta.vector for delta in learner_deltas},
                    token_counts=token_counts,
                    outer_lr=float(getattr(self.optimizer, "outer_lr", 1.0)),
                    chunk_elements=max(1, min(1024, self.global_vector.size)),
                )
            streaming_values = (
                streaming.result.new_values
                if hasattr(streaming, "result")
                else streaming.new_values
            )
            if not np.allclose(
                streaming_values,
                merge_result.new_global_vector,
                rtol=0.0,
                atol=1e-12,
            ):
                raise InvariantViolation("streaming_chunked merge differs from in-memory merge")
            self.metrics.live_streaming_merges += 1
            self.metrics.live_streaming_merge_bytes_read += (
                streaming.result.metrics.streaming_merge_bytes_read
                if hasattr(streaming, "result")
                else streaming.metrics.streaming_merge_bytes_read
            )
            self.metrics.live_streaming_merge_bytes_written += (
                streaming.result.metrics.streaming_merge_bytes_written
                if hasattr(streaming, "result")
                else streaming.metrics.streaming_merge_bytes_written
            )
            self.metrics.live_streaming_merge_chunks_processed += (
                streaming.result.metrics.streaming_merge_chunks_processed
                if hasattr(streaming, "result")
                else streaming.metrics.streaming_merge_chunks_processed
            )
            self.metrics.live_streaming_merge_peak_working_bytes_estimate = max(
                self.metrics.live_streaming_merge_peak_working_bytes_estimate,
                streaming.peak_working_bytes_estimate
                if hasattr(streaming, "peak_working_bytes_estimate")
                else streaming.metrics.streaming_merge_peak_working_bytes_estimate,
            )
            self.metrics.numeric_merge_performed = True
            if binary_refs:
                self.metrics.binary_streaming_merges += 1
                self.metrics.binary_streaming_merge_bytes_read += (
                    streaming.bytes_read
                    if hasattr(streaming, "bytes_read")
                    else streaming.metrics.streaming_merge_bytes_read
                )
                self.metrics.binary_streaming_merge_bytes_written += (
                    streaming.bytes_written
                    if hasattr(streaming, "bytes_written")
                    else streaming.metrics.streaming_merge_bytes_written
                )
                self.metrics.binary_streaming_merge_chunks_read += (
                    streaming.chunks_read
                    if hasattr(streaming, "chunks_read")
                    else streaming.metrics.streaming_merge_chunks_processed
                    * max(len(learner_deltas), 1)
                )
                self.metrics.binary_streaming_merge_chunks_written += (
                    streaming.chunks_written
                    if hasattr(streaming, "chunks_written")
                    else streaming.metrics.streaming_merge_chunks_processed
                )
                self.metrics.binary_streaming_merge_peak_working_bytes_estimate = max(
                    self.metrics.binary_streaming_merge_peak_working_bytes_estimate,
                    streaming.peak_working_bytes_estimate
                    if hasattr(streaming, "peak_working_bytes_estimate")
                    else streaming.metrics.streaming_merge_peak_working_bytes_estimate,
                )
                self.metrics.binary_streaming_merge_wall_time_seconds += (
                    streaming.wall_time_seconds
                    if hasattr(streaming, "wall_time_seconds")
                    else 0.0
                )
        else:
            merge_result = token_weighted_merge(
                self.global_vector,
                learner_deltas,
                optimizer=self.optimizer,
            )

        old_vector = self.global_vector.copy()
        previous_version = self.global_version
        self.global_vector = merge_result.new_global_vector.copy()
        self.global_version += 1
        if self.global_version != previous_version + 1:
            raise InvariantViolation("global_version must increase by exactly one per commit")

        accepted_fragment_artifacts = {
            update.learner_id: self.pending_artifact_refs.get(update.learner_id)
            for update in accepted_updates
            if self.pending_artifact_refs.get(update.learner_id) is not None
        }

        for learner_id in merge_result.included_learner_ids:
            self.pending.pop(learner_id, None)
            self.pending_artifact_refs.pop(learner_id, None)

        self.metrics.accepted_updates += len(merge_result.included_learner_ids)
        self.metrics.useful_tokens += merge_result.useful_tokens
        self.metrics.sync_rounds_committed += 1
        self.metrics.quorum_compositions.append(merge_result.included_learner_ids)

        merge_decision = MergeDecision(
            round_id=round_id,
            previous_global_version=previous_version,
            new_global_version=self.global_version,
            accepted_learner_ids=merge_result.included_learner_ids,
            token_weights=merge_result.token_weights,
            useful_tokens=merge_result.useful_tokens,
            outer_optimizer=optimizer_name,
            outer_lr=float(getattr(self.optimizer, "outer_lr", 1.0)),
            outer_momentum=float(outer_momentum) if outer_momentum is not None else None,
            old_global_vector=old_vector.tolist(),
            weighted_delta=merge_result.weighted_delta.tolist(),
            new_global_vector=self.global_vector.tolist(),
        )
        commit_payload: dict[str, Any] = merge_decision.model_dump(mode="json")
        if (
            self.event_payload_mode == "chunked"
            and self.global_vector_artifact_writer is not None
        ):
            old_ref = self.global_vector_artifact_writer(
                "old_global_vector",
                old_vector,
                previous_version,
            )
            delta_ref = self.global_vector_artifact_writer(
                "weighted_delta",
                merge_result.weighted_delta,
                self.global_version,
            )
            new_ref = self.global_vector_artifact_writer(
                "new_global_vector",
                self.global_vector,
                self.global_version,
            )
            commit_payload = {
                "round_id": round_id,
                "previous_global_version": previous_version,
                "new_global_version": self.global_version,
                "accepted_learner_ids": merge_result.included_learner_ids,
                "token_weights": merge_result.token_weights,
                "useful_tokens": merge_result.useful_tokens,
                "outer_optimizer": optimizer_name,
                "outer_lr": float(getattr(self.optimizer, "outer_lr", 1.0)),
                "outer_momentum": (
                    float(outer_momentum) if outer_momentum is not None else None
                ),
                "numeric_merge_performed": True,
                "simulation_only": False,
                "merge_mode": self.merge_mode,
                "accepted_fragment_artifacts": accepted_fragment_artifacts,
                "old_global_vector_artifact_ref": old_ref,
                "weighted_delta_artifact_ref": delta_ref,
                "new_global_vector_artifact_ref": new_ref,
            }
        self.event_log.append(
            EventType.SYNC_ROUND_COMMITTED,
            logical_time=current_tick,
            round_id=round_id,
            payload=commit_payload,
        )
        self.tracker.reset()
        return merge_decision

    def write_checkpoint(self, *, checkpoint_id: str, logical_time: int) -> CheckpointRecord:
        checkpoint = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            global_version=self.global_version,
            logical_time=logical_time,
            global_vector=self.global_vector.tolist(),
            metrics={
                "accepted_updates": self.metrics.accepted_updates,
                "rejected_updates": self.metrics.rejected_updates,
                "useful_tokens": self.metrics.useful_tokens,
                "sync_rounds_committed": self.metrics.sync_rounds_committed,
            },
        )
        payload = checkpoint.model_dump(mode="json")
        if (
            self.event_payload_mode == "chunked"
            and self.global_vector_artifact_writer is not None
        ):
            payload = {
                "checkpoint_id": checkpoint_id,
                "global_version": self.global_version,
                "logical_time": logical_time,
                "global_vector_artifact_ref": self.global_vector_artifact_writer(
                    "checkpoint_global_vector",
                    self.global_vector,
                    self.global_version,
                ),
                "metrics": checkpoint.metrics,
            }
        self.event_log.append(
            EventType.CHECKPOINT_WRITTEN,
            logical_time=logical_time,
            round_id=None,
            payload=payload,
        )
        return checkpoint
