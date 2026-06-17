"""Toy vector model helpers for CPU-only synchronization tests."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from decodilo.protocol.messages import ModelFragment


def make_initial_vector(dimension: int) -> NDArray[np.float64]:
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    return np.zeros(dimension, dtype=np.float64)


def make_target_vector(dimension: int, *, seed: int) -> NDArray[np.float64]:
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=1.0, size=dimension).astype(np.float64)


def convex_loss(vector: NDArray[np.float64], target: NDArray[np.float64]) -> float:
    params = np.asarray(vector, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)
    if params.shape != target_array.shape:
        raise ValueError("vector and target shapes must match")
    diff = params - target_array
    return float(np.dot(diff, diff))


def split_vector(
    vector: NDArray[np.float64],
    *,
    num_fragments: int,
    global_version: int,
    source_learner_id: str | None,
    tokens_since_last_sync: int,
    created_at: int,
) -> list[ModelFragment]:
    array = np.asarray(vector, dtype=np.float64)
    if array.ndim != 1 or array.size == 0:
        raise ValueError("vector must be a non-empty 1D vector")
    if num_fragments <= 0:
        raise ValueError("num_fragments must be positive")

    chunks = np.array_split(array, num_fragments)
    fragments: list[ModelFragment] = []
    source = source_learner_id or "global"
    for index, chunk in enumerate(chunks):
        if chunk.size == 0:
            continue
        fragments.append(
            ModelFragment(
                fragment_id=f"{source}:v{global_version}:f{index}",
                global_version=global_version,
                vector_data=chunk.astype(float).tolist(),
                source_learner_id=source_learner_id,
                tokens_since_last_sync=tokens_since_last_sync,
                created_at=created_at,
            )
        )
    return fragments


def join_fragments(fragments: list[ModelFragment]) -> NDArray[np.float64]:
    if not fragments:
        raise ValueError("fragments must not be empty")
    ordered = sorted(fragments, key=lambda fragment: fragment.fragment_id)
    return np.asarray(
        [value for fragment in ordered for value in fragment.vector_data],
        dtype=np.float64,
    )
