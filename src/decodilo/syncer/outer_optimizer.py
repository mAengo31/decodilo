"""Outer optimizer interfaces for applying aggregated DiLoCo-style deltas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class OuterOptimizer(Protocol):
    """Protocol implemented by syncer-side optimizers."""

    def apply(
        self,
        global_vector: NDArray[np.float64],
        weighted_delta: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Apply an aggregate learner delta to the current global vector."""


@dataclass(frozen=True)
class SGDOuterOptimizer:
    """Simple SGD-style outer optimizer.

    W_new = W_global + outer_lr * weighted_delta
    """

    outer_lr: float = 1.0

    def apply(
        self,
        global_vector: NDArray[np.float64],
        weighted_delta: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        if self.outer_lr < 0:
            raise ValueError("outer_lr must be non-negative")
        return np.asarray(global_vector, dtype=np.float64) + self.outer_lr * np.asarray(
            weighted_delta,
            dtype=np.float64,
        )


@dataclass(frozen=True)
class FutureOuterOptimizerSpec:
    """Typed marker for optimizers intentionally left outside this milestone."""

    name: str
    parameters: dict[str, float]

    def describe(self) -> str:
        return f"{self.name} outer optimizer spec with {len(self.parameters)} parameters"


NESTEROV_OUTER_OPTIMIZER = FutureOuterOptimizerSpec(
    name="nesterov",
    parameters={"momentum": 0.9},
)
ADAM_OUTER_OPTIMIZER = FutureOuterOptimizerSpec(
    name="adam",
    parameters={"beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8},
)
