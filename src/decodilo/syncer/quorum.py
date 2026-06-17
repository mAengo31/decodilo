"""Quorum policy and state machine for asynchronous learner updates."""

from __future__ import annotations

from dataclasses import dataclass

from decodilo.protocol.ids import make_round_id
from decodilo.protocol.messages import QuorumDecision


@dataclass(frozen=True)
class PendingUpdate:
    """A learner update waiting for a sync decision."""

    learner_id: str
    global_version_seen: int
    tokens: int
    submitted_at: int


@dataclass(frozen=True)
class QuorumPolicy:
    """Policy controlling when a sync round may commit."""

    min_quorum: int
    grace_window_ticks: int = 0
    max_staleness_versions: int = 0
    allow_partial_round: bool = False

    def __post_init__(self) -> None:
        if self.min_quorum <= 0:
            raise ValueError("min_quorum must be positive")
        if self.grace_window_ticks < 0:
            raise ValueError("grace_window_ticks must be non-negative")
        if self.max_staleness_versions < 0:
            raise ValueError("max_staleness_versions must be non-negative")


@dataclass
class QuorumTracker:
    """Stateful quorum evaluator with a grace window after quorum is reached."""

    policy: QuorumPolicy
    first_update_tick: int | None = None
    quorum_reached_tick: int | None = None

    def reset(self) -> None:
        self.first_update_tick = None
        self.quorum_reached_tick = None

    def decide(
        self,
        pending_updates: list[PendingUpdate],
        *,
        current_version: int,
        current_tick: int,
        failed_learner_ids: set[str] | None = None,
    ) -> QuorumDecision:
        failed = failed_learner_ids or set()
        rejected: dict[str, str] = {}
        eligible: list[PendingUpdate] = []

        for update in pending_updates:
            staleness = current_version - update.global_version_seen
            if staleness > self.policy.max_staleness_versions:
                rejected[update.learner_id] = "stale"
            elif update.learner_id in failed:
                rejected[update.learner_id] = "failed"
            elif update.tokens <= 0:
                rejected[update.learner_id] = "zero_tokens"
            else:
                eligible.append(update)

        if eligible and self.first_update_tick is None:
            self.first_update_tick = min(update.submitted_at for update in eligible)

        accepted_ids = [
            update.learner_id
            for update in sorted(eligible, key=lambda item: item.learner_id)
        ]
        if len(eligible) >= self.policy.min_quorum:
            if self.quorum_reached_tick is None:
                self.quorum_reached_tick = current_tick
            if current_tick - self.quorum_reached_tick >= self.policy.grace_window_ticks:
                return QuorumDecision(
                    should_commit=True,
                    round_id=make_round_id(current_version),
                    current_tick=current_tick,
                    accepted_learner_ids=accepted_ids,
                    rejected_learner_ids=rejected,
                    grace_started_at=self.quorum_reached_tick,
                    reason="quorum_reached",
                )
            return QuorumDecision(
                should_commit=False,
                round_id=make_round_id(current_version),
                current_tick=current_tick,
                accepted_learner_ids=accepted_ids,
                rejected_learner_ids=rejected,
                grace_started_at=self.quorum_reached_tick,
                reason="within_grace_window",
            )

        if (
            self.policy.allow_partial_round
            and eligible
            and self.first_update_tick is not None
            and current_tick - self.first_update_tick >= self.policy.grace_window_ticks
        ):
            return QuorumDecision(
                should_commit=True,
                round_id=make_round_id(current_version),
                current_tick=current_tick,
                accepted_learner_ids=accepted_ids,
                rejected_learner_ids=rejected,
                grace_started_at=self.first_update_tick,
                reason="partial_round_allowed",
            )

        return QuorumDecision(
            should_commit=False,
            round_id=make_round_id(current_version),
            current_tick=current_tick,
            accepted_learner_ids=accepted_ids,
            rejected_learner_ids=rejected,
            grace_started_at=self.quorum_reached_tick,
            reason="below_quorum",
        )
