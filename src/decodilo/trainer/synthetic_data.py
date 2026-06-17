"""Deterministic synthetic data streams for optional trainer adapters."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


def deterministic_seed(*parts: object) -> int:
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


@dataclass(frozen=True)
class SyntheticBatch:
    inputs: np.ndarray
    targets: np.ndarray
    token_count: int


def make_synthetic_regression_batch(
    *,
    run_id: str,
    learner_id: str,
    seed: int,
    local_step: int,
    batch_size: int,
    input_dim: int,
    output_dim: int,
    token_count: int | None = None,
) -> SyntheticBatch:
    """Return a stable synthetic regression batch."""

    if min(batch_size, input_dim, output_dim) <= 0:
        raise ValueError("batch_size, input_dim, and output_dim must be positive")
    rng = np.random.default_rng(
        deterministic_seed(run_id, learner_id, seed, local_step, batch_size, input_dim, output_dim)
    )
    inputs = rng.normal(size=(batch_size, input_dim)).astype(np.float32)
    true_weight = rng.normal(size=(input_dim, output_dim)).astype(np.float32)
    targets = inputs @ true_weight
    return SyntheticBatch(
        inputs=inputs,
        targets=targets.astype(np.float32),
        token_count=token_count if token_count is not None else batch_size,
    )


def make_synthetic_token_batch(
    *,
    run_id: str,
    learner_id: str,
    seed: int,
    local_step: int,
    batch_size: int,
    seq_len: int,
    vocab_size: int,
) -> SyntheticBatch:
    """Return deterministic next-token data for tiny causal LM tests."""

    if min(batch_size, seq_len, vocab_size) <= 0:
        raise ValueError("batch_size, seq_len, and vocab_size must be positive")
    rng = np.random.default_rng(
        deterministic_seed(run_id, learner_id, seed, local_step, batch_size, seq_len, vocab_size)
    )
    inputs = rng.integers(0, vocab_size, size=(batch_size, seq_len), dtype=np.int64)
    targets = (inputs + 1) % vocab_size
    return SyntheticBatch(
        inputs=inputs,
        targets=targets.astype(np.int64),
        token_count=batch_size * seq_len,
    )
