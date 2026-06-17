"""Trainer adapter interface used by local learner workers."""

from __future__ import annotations

from typing import Any, Protocol

from decodilo.trainer.state import (
    TrainerConfig,
    TrainerFragment,
    TrainerHealth,
    TrainerState,
    TrainStepResult,
)


class TrainerAdapter(Protocol):
    """Boundary between runtime/process logic and local training implementation."""

    def initialize(
        self,
        *,
        run_id: str,
        learner_id: str,
        seed: int,
        initial_state: TrainerState | None,
        config: TrainerConfig,
    ) -> None:
        """Initialize or restore the trainer."""

    def train_local_steps(self, num_steps: int) -> TrainStepResult:
        """Run local training and return step/token accounting."""

    def get_state_fragments(self, fragment_ids: list[int] | None = None) -> list[TrainerFragment]:
        """Return typed fragments for the current local state."""

    def apply_global_update(
        self,
        fragments: list[TrainerFragment],
        *,
        global_version: int,
    ) -> None:
        """Apply global fragments from the syncer."""

    def get_full_state(self) -> TrainerState:
        """Return full trainer state."""

    def set_full_state(self, state: TrainerState, *, global_version: int) -> None:
        """Replace full trainer state and set the observed global version."""

    def checkpoint_payload(self) -> dict[str, Any]:
        """Return stable checkpoint payload data."""

    def restore_from_checkpoint(self, payload: dict[str, Any]) -> None:
        """Restore from a checkpoint payload."""

    def estimate_state_bytes(self) -> int:
        """Estimate serialized model state bytes."""

    def health(self) -> TrainerHealth:
        """Return trainer health and accounting state."""
