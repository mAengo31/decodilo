"""Streaming merge over tensor_binary_v1 fragment artifacts."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from decodilo.runtime.artifact_transport import LocalArtifactTransport
from decodilo.syncer.merge_plan import MergePlan, normalized_token_weights
from decodilo.syncer.out_of_core_merge import out_of_core_token_weighted_merge
from decodilo.syncer.streaming_merge import StreamingMergeMetrics, StreamingMergeResult


@dataclass(frozen=True)
class BinaryStreamingMergeReport:
    result: StreamingMergeResult
    bytes_read: int
    bytes_written: int
    chunks_read: int
    chunks_written: int
    wall_time_seconds: float
    merge_plan: MergePlan | None = None
    peak_working_bytes_estimate: int = 0


def binary_streaming_token_weighted_merge(
    *,
    global_values: np.ndarray,
    fragment_refs: dict[str, dict],
    token_counts: dict[str, int],
    transport: LocalArtifactTransport,
    outer_lr: float = 1.0,
    chunk_elements: int = 1024,
) -> BinaryStreamingMergeReport:
    started = time.perf_counter()
    bytes_read = 0
    chunks_read = 0
    binary_refs: dict[str, dict] = {}
    for learner_id, ref in fragment_refs.items():
        manifest = transport.validate_ref(ref)
        bytes_read += manifest.total_bytes
        chunks_read += len(manifest.chunk_hashes)
        binary_refs[learner_id] = ref
    dtype = str(np.asarray(global_values).dtype)
    if dtype not in {"float16", "float32", "float64"}:
        dtype = "float64"
    max_working_bytes = max(
        np.dtype(dtype).itemsize * max(chunk_elements, 1) * (len(binary_refs) + 3),
        np.dtype(dtype).itemsize * (len(binary_refs) + 3),
    )
    plan = MergePlan(
        run_id=str(next(iter(binary_refs.values())).get("run_id", "run")) if binary_refs else "run",
        round_id="binary-streaming-merge",
        fragment_id=0,
        input_artifact_refs=binary_refs,
        token_weights=normalized_token_weights(token_counts),
        outer_lr=outer_lr,
        dtype=dtype,
        shape=list(np.asarray(global_values).shape),
        total_elements=int(np.asarray(global_values).size),
        chunk_size_bytes=max(int(np.dtype(dtype).itemsize * max(chunk_elements, 1)), 1),
        max_working_bytes=max_working_bytes,
    )
    out_of_core = out_of_core_token_weighted_merge(
        plan=plan,
        global_values=np.asarray(global_values, dtype=np.dtype(dtype)),
        transport=transport,
    )
    result = StreamingMergeResult(
        new_values=out_of_core.new_values,
        metadata_only=False,
        numeric_merge_performed=True,
        simulation_only=False,
        lineage_hash=out_of_core.lineage_hash,
        metrics=StreamingMergeMetrics(
            streaming_merge_bytes_read=out_of_core.metrics.merge_input_bytes_read,
            streaming_merge_bytes_written=out_of_core.metrics.merge_output_bytes_written,
            streaming_merge_chunks_processed=out_of_core.metrics.merge_blocks_processed,
            streaming_merge_peak_working_bytes_estimate=(
                out_of_core.metrics.merge_peak_working_bytes_estimate
            ),
        ),
        token_weights=out_of_core.token_weights,
    )
    bytes_written = int(result.new_values.nbytes if result.new_values is not None else 0)
    chunks_written = max(result.metrics.streaming_merge_chunks_processed, 0)
    return BinaryStreamingMergeReport(
        result=result,
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        chunks_read=chunks_read,
        chunks_written=chunks_written,
        wall_time_seconds=time.perf_counter() - started,
        merge_plan=plan,
        peak_working_bytes_estimate=result.metrics.streaming_merge_peak_working_bytes_estimate,
    )
