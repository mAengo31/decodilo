"""Outer optimizer interfaces for applying aggregated DiLoCo-style deltas."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class NesterovOuterOptimizer:
    """Stateful DiLoCo-style Nesterov outer optimizer over pseudo-gradients."""

    outer_lr: float = 1.0
    momentum: float = 0.9
    velocity: NDArray[np.float64] | None = field(default=None)
    step: int = 0

    def apply(
        self,
        global_vector: NDArray[np.float64],
        weighted_delta: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        if self.outer_lr < 0:
            raise ValueError("outer_lr must be non-negative")
        if self.momentum < 0:
            raise ValueError("momentum must be non-negative")
        base = np.asarray(global_vector, dtype=np.float64)
        delta = np.asarray(weighted_delta, dtype=np.float64)
        if delta.shape != base.shape:
            raise ValueError("weighted_delta shape must match global_vector")
        pseudo_gradient = -delta
        if self.velocity is None:
            self.velocity = np.zeros_like(base)
        if self.velocity.shape != base.shape:
            raise ValueError("nesterov velocity shape must match global_vector")
        next_velocity = self.momentum * self.velocity + pseudo_gradient
        nesterov_direction = pseudo_gradient + self.momentum * next_velocity
        self.velocity = next_velocity
        self.step += 1
        return base - self.outer_lr * nesterov_direction

    def state_dict(self) -> dict[str, object]:
        return {
            "outer_optimizer": "nesterov",
            "outer_optimizer_semantics": "nesterov",
            "outer_lr": self.outer_lr,
            "momentum": self.momentum,
            "step": self.step,
            "velocity": [] if self.velocity is None else self.velocity.astype(float).tolist(),
        }


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


def create_outer_optimizer(
    name: str,
    *,
    outer_lr: float,
    momentum: float = 0.9,
) -> OuterOptimizer:
    normalized = name.lower().replace("-", "_")
    if normalized == "sgd":
        return SGDOuterOptimizer(outer_lr=outer_lr)
    if normalized == "nesterov":
        return NesterovOuterOptimizer(outer_lr=outer_lr, momentum=momentum)
    raise ValueError(f"unknown outer optimizer {name!r}")


def outer_optimizer_name(optimizer: OuterOptimizer) -> str:
    if isinstance(optimizer, NesterovOuterOptimizer):
        return "nesterov"
    if isinstance(optimizer, SGDOuterOptimizer):
        return "sgd"
    return optimizer.__class__.__name__.lower()


def outer_optimizer_state(optimizer: OuterOptimizer) -> dict[str, object]:
    if hasattr(optimizer, "state_dict"):
        return dict(optimizer.state_dict())  # type: ignore[call-arg]
    return {
        "outer_optimizer": outer_optimizer_name(optimizer),
        "outer_lr": float(getattr(optimizer, "outer_lr", 1.0)),
    }
