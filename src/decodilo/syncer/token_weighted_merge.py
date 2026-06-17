"""Token-weighted merge for learner vectors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from decodilo.syncer.outer_optimizer import OuterOptimizer, SGDOuterOptimizer


@dataclass(frozen=True)
class LearnerDelta:
    """A learner's full-vector update as seen by the syncer."""

    learner_id: str
    vector: NDArray[np.float64]
    tokens: int
    global_version_seen: int


@dataclass(frozen=True)
class TokenWeightedMergeResult:
    """Result of a token-weighted merge."""

    new_global_vector: NDArray[np.float64]
    weighted_delta: NDArray[np.float64]
    token_weights: dict[str, float]
    included_learner_ids: list[str]
    useful_tokens: int


def _as_vector(vector: NDArray[np.float64], *, name: str) -> NDArray[np.float64]:
    array = np.asarray(vector, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a 1D vector")
    if array.size == 0:
        raise ValueError(f"{name} must not be empty")
    return array


def token_weighted_merge(
    global_vector: NDArray[np.float64],
    updates: list[LearnerDelta],
    *,
    optimizer: OuterOptimizer | None = None,
    excluded_learner_ids: set[str] | None = None,
) -> TokenWeightedMergeResult:
    """Merge learner vectors by weighting each delta by useful token count.

    The delta for learner i is W_i - W_global. Learners with zero tokens or
    learner ids in excluded_learner_ids do not affect the aggregate.
    """

    base = _as_vector(global_vector, name="global_vector")
    excluded = excluded_learner_ids or set()
    included = [
        update
        for update in updates
        if update.tokens > 0 and update.learner_id not in excluded
    ]

    if not included:
        zero = np.zeros_like(base)
        opt = optimizer or SGDOuterOptimizer()
        return TokenWeightedMergeResult(
            new_global_vector=opt.apply(base, zero),
            weighted_delta=zero,
            token_weights={},
            included_learner_ids=[],
            useful_tokens=0,
        )

    total_tokens = sum(update.tokens for update in included)
    weighted_delta = np.zeros_like(base)
    token_weights: dict[str, float] = {}

    for update in included:
        vector = _as_vector(update.vector, name=f"vector[{update.learner_id}]")
        if vector.shape != base.shape:
            raise ValueError(
                f"vector[{update.learner_id}] shape {vector.shape} does not match {base.shape}"
            )
        weight = update.tokens / total_tokens
        token_weights[update.learner_id] = weight
        weighted_delta += weight * (vector - base)

    opt = optimizer or SGDOuterOptimizer()
    return TokenWeightedMergeResult(
        new_global_vector=opt.apply(base, weighted_delta),
        weighted_delta=weighted_delta,
        token_weights=token_weights,
        included_learner_ids=[update.learner_id for update in included],
        useful_tokens=total_tokens,
    )

