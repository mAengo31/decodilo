"""Simulation metrics produced by the CPU runner."""

from __future__ import annotations

from dataclasses import dataclass, field

from decodilo.errors import InvariantViolation


@dataclass(frozen=True)
class LearnerUptime:
    learner_id: str
    alive_ticks: int
    paused_ticks: int
    failed_ticks: int


@dataclass(frozen=True)
class SimulationMetrics:
    total_tokens_processed: int
    useful_tokens_accepted: int
    rejected_tokens: int
    stale_tokens: int
    wasted_tokens: int
    committed_sync_rounds: int
    skipped_sync_rounds: int
    rejected_fragments: int
    stale_fragments: int
    learner_uptime_ticks: dict[str, int] = field(default_factory=dict)
    learner_failed_ticks: dict[str, int] = field(default_factory=dict)
    learner_paused_ticks: dict[str, int] = field(default_factory=dict)
    goodput_ratio: float = 0.0
    estimated_cost: float | None = None
    cost_per_total_token: float | None = None
    cost_per_useful_token: float | None = None
    accepted_updates: int = 0
    final_loss: float = 0.0
    learner_uptime: dict[str, LearnerUptime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total_tokens_processed < 0:
            raise InvariantViolation("total_tokens_processed cannot be negative")
        if self.useful_tokens_accepted < 0:
            raise InvariantViolation("useful_tokens_accepted cannot be negative")
        if self.useful_tokens_accepted > self.total_tokens_processed:
            raise InvariantViolation("useful_tokens_accepted cannot exceed total tokens")
        if self.wasted_tokens != self.total_tokens_processed - self.useful_tokens_accepted:
            raise InvariantViolation("wasted_tokens must equal total_tokens_processed - useful")
        if not 0.0 <= self.goodput_ratio <= 1.0:
            raise InvariantViolation("goodput_ratio must be in [0, 1]")
        if (
            self.cost_per_total_token is not None
            and self.cost_per_useful_token is not None
            and self.cost_per_useful_token < self.cost_per_total_token
        ):
            raise InvariantViolation(
                "cost_per_useful_token must be >= cost_per_total_token"
            )

    @property
    def sync_rounds_committed(self) -> int:
        """Backward-compatible alias for Milestone 001 tests."""

        return self.committed_sync_rounds

    @property
    def rejected_updates(self) -> int:
        """Backward-compatible alias for rejected fragment count."""

        return self.rejected_fragments

