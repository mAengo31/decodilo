"""Backpressure limits and accounting for local runtime submissions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BackpressureConfig:
    max_pending_messages_per_learner: int = 128
    max_pending_fragments_per_learner: int = 1
    max_inflight_bytes_per_learner: int = 2_000_000
    max_total_inflight_bytes: int = 10_000_000
    submit_fragment_timeout_seconds: float = 2.0


@dataclass
class BackpressureMetrics:
    backpressure_rejections: int = 0
    pending_messages_current: int = 0
    pending_fragments_current: int = 0
    inflight_bytes_current: int = 0
    inflight_bytes_peak: int = 0
    message_count_pressure: int = 0
    byte_pressure: int = 0
    memory_budget_pressure: int = 0
    spill_budget_pressure: int = 0


@dataclass
class BackpressureState:
    config: BackpressureConfig = field(default_factory=BackpressureConfig)
    metrics: BackpressureMetrics = field(default_factory=BackpressureMetrics)
    pending_messages_by_learner: dict[str, int] = field(default_factory=dict)
    pending_fragments_by_learner: dict[str, int] = field(default_factory=dict)
    inflight_bytes_by_learner: dict[str, int] = field(default_factory=dict)

    def can_accept_fragment(self, learner_id: str, *, message_bytes: int) -> tuple[bool, str]:
        pending_messages = self.pending_messages_by_learner.get(learner_id, 0)
        pending_fragments = self.pending_fragments_by_learner.get(learner_id, 0)
        learner_bytes = self.inflight_bytes_by_learner.get(learner_id, 0)
        total_bytes = self.metrics.inflight_bytes_current

        if pending_messages >= self.config.max_pending_messages_per_learner:
            return False, "max_pending_messages_per_learner"
        if pending_fragments >= self.config.max_pending_fragments_per_learner:
            return False, "max_pending_fragments_per_learner"
        if learner_bytes + message_bytes > self.config.max_inflight_bytes_per_learner:
            return False, "max_inflight_bytes_per_learner"
        if total_bytes + message_bytes > self.config.max_total_inflight_bytes:
            return False, "max_total_inflight_bytes"
        return True, "accepted"

    def reject(self, reason: str = "backpressure") -> None:
        self.metrics.backpressure_rejections += 1
        if "pending_messages" in reason or "pending_fragments" in reason:
            self.metrics.message_count_pressure += 1
        elif "memory" in reason:
            self.metrics.memory_budget_pressure += 1
        elif "spill" in reason:
            self.metrics.spill_budget_pressure += 1
        else:
            self.metrics.byte_pressure += 1

    def begin_fragment(self, learner_id: str, *, message_bytes: int) -> None:
        self.pending_messages_by_learner[learner_id] = (
            self.pending_messages_by_learner.get(learner_id, 0) + 1
        )
        self.pending_fragments_by_learner[learner_id] = (
            self.pending_fragments_by_learner.get(learner_id, 0) + 1
        )
        self.inflight_bytes_by_learner[learner_id] = (
            self.inflight_bytes_by_learner.get(learner_id, 0) + message_bytes
        )
        self.metrics.pending_messages_current += 1
        self.metrics.pending_fragments_current += 1
        self.metrics.inflight_bytes_current += message_bytes
        self.metrics.inflight_bytes_peak = max(
            self.metrics.inflight_bytes_peak,
            self.metrics.inflight_bytes_current,
        )

    def end_fragment(self, learner_id: str, *, message_bytes: int) -> None:
        self.pending_messages_by_learner[learner_id] = max(
            self.pending_messages_by_learner.get(learner_id, 0) - 1,
            0,
        )
        self.pending_fragments_by_learner[learner_id] = max(
            self.pending_fragments_by_learner.get(learner_id, 0) - 1,
            0,
        )
        self.inflight_bytes_by_learner[learner_id] = max(
            self.inflight_bytes_by_learner.get(learner_id, 0) - message_bytes,
            0,
        )
        self.metrics.pending_messages_current = max(self.metrics.pending_messages_current - 1, 0)
        self.metrics.pending_fragments_current = max(self.metrics.pending_fragments_current - 1, 0)
        self.metrics.inflight_bytes_current = max(
            self.metrics.inflight_bytes_current - message_bytes,
            0,
        )
