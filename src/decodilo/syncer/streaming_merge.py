"""Chunk-by-chunk token-weighted merge helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.storage.checksums import sha256_bytes


@dataclass(frozen=True)
class StreamingLearnerFragment:
    learner_id: str
    chunks: list[bytes]
    tokens: int
    dtype: str = "float64"
    shape: tuple[int, ...] = ()
    checksum: str | None = None


@dataclass
class StreamingMergeMetrics:
    streaming_merge_bytes_read: int = 0
    streaming_merge_bytes_written: int = 0
    streaming_merge_chunks_processed: int = 0
    streaming_merge_peak_working_bytes_estimate: int = 0


@dataclass(frozen=True)
class StreamingMergeResult:
    new_values: np.ndarray | None
    metadata_only: bool
    numeric_merge_performed: bool
    simulation_only: bool
    lineage_hash: str
    metrics: StreamingMergeMetrics
    token_weights: dict[str, float] = field(default_factory=dict)


def _array_chunks(array: np.ndarray, *, chunk_elements: int) -> Iterable[np.ndarray]:
    flat = np.asarray(array, dtype=np.float64).reshape(-1)
    for index in range(0, flat.size, chunk_elements):
        yield flat[index : index + chunk_elements]


def streaming_token_weighted_merge(
    *,
    global_values: np.ndarray,
    learner_values: dict[str, np.ndarray],
    token_counts: dict[str, int],
    outer_lr: float = 1.0,
    chunk_elements: int = 1024,
) -> StreamingMergeResult:
    """Streaming equivalent of W_new = W_global + lr * weighted_delta."""

    global_flat = np.asarray(global_values, dtype=np.float64).reshape(-1)
    if chunk_elements <= 0:
        raise ValueError("chunk_elements must be positive")
    total_tokens = sum(max(tokens, 0) for tokens in token_counts.values())
    weights = {
        learner_id: (max(tokens, 0) / total_tokens if total_tokens else 0.0)
        for learner_id, tokens in token_counts.items()
    }
    output = np.empty_like(global_flat)
    metrics = StreamingMergeMetrics()
    for offset in range(0, global_flat.size, chunk_elements):
        stop = min(offset + chunk_elements, global_flat.size)
        global_chunk = global_flat[offset:stop]
        weighted_delta = np.zeros_like(global_chunk)
        for learner_id, values in learner_values.items():
            raw = np.asarray(values)
            if raw.shape != np.asarray(global_values).shape:
                raise InvariantViolation("learner fragment shape does not match global fragment")
            if raw.dtype.kind not in {"f", "i", "u"}:
                raise InvariantViolation("learner fragment dtype must be numeric")
            learner_flat = raw.astype(np.float64).reshape(-1)
            learner_chunk = learner_flat[offset:stop]
            weighted_delta += weights.get(learner_id, 0.0) * (learner_chunk - global_chunk)
            metrics.streaming_merge_bytes_read += learner_chunk.nbytes
        output[offset:stop] = global_chunk + outer_lr * weighted_delta
        metrics.streaming_merge_bytes_read += global_chunk.nbytes
        metrics.streaming_merge_bytes_written += output[offset:stop].nbytes
        metrics.streaming_merge_chunks_processed += 1
        metrics.streaming_merge_peak_working_bytes_estimate = max(
            metrics.streaming_merge_peak_working_bytes_estimate,
            global_chunk.nbytes * (len(learner_values) + 2),
        )
    return StreamingMergeResult(
        new_values=output.reshape(np.asarray(global_values).shape),
        metadata_only=False,
        numeric_merge_performed=True,
        simulation_only=False,
        lineage_hash=sha256_bytes(output.tobytes()),
        metrics=metrics,
        token_weights=weights,
    )


def validate_streaming_fragment(fragment: StreamingLearnerFragment) -> None:
    data = b"".join(fragment.chunks)
    if fragment.checksum is not None and sha256_bytes(data) != fragment.checksum:
        raise InvariantViolation("streaming fragment checksum mismatch")


def metadata_only_merge_dry_run(
    *,
    fragment_hashes: dict[str, str],
    payload_bytes: dict[str, int],
    token_counts: dict[str, int],
) -> StreamingMergeResult:
    total_tokens = sum(max(tokens, 0) for tokens in token_counts.values())
    weights = {
        learner_id: (max(tokens, 0) / total_tokens if total_tokens else 0.0)
        for learner_id, tokens in token_counts.items()
    }
    lineage = sha256_bytes(
        repr(
            {
                "fragment_hashes": sorted(fragment_hashes.items()),
                "payload_bytes": sorted(payload_bytes.items()),
                "weights": sorted(weights.items()),
            }
        ).encode("utf-8")
    )
    return StreamingMergeResult(
        new_values=None,
        metadata_only=True,
        numeric_merge_performed=False,
        simulation_only=True,
        lineage_hash=lineage,
        metrics=StreamingMergeMetrics(
            streaming_merge_bytes_read=sum(payload_bytes.values()),
            streaming_merge_bytes_written=0,
            streaming_merge_chunks_processed=len(fragment_hashes),
            streaming_merge_peak_working_bytes_estimate=0,
        ),
        token_weights=weights,
    )
