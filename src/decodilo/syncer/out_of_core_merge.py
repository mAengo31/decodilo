"""Memory-bounded binary tensor artifact merge."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import LocalArtifactTransport
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.range_reader import read_ref_range
from decodilo.storage.tensor_artifact import write_tensor_artifact
from decodilo.syncer.merge_plan import MergePlan, normalized_token_weights
from decodilo.syncer.merge_validation import validate_merge_specs


@dataclass(frozen=True)
class OutOfCoreMergeMetrics:
    out_of_core_merges: int = 0
    merge_blocks_processed: int = 0
    merge_input_bytes_read: int = 0
    merge_output_bytes_written: int = 0
    merge_peak_working_bytes_estimate: int = 0
    merge_wall_time_seconds: float = 0.0
    merge_rechunk_count: int = 0
    merge_validation_failures: int = 0


@dataclass(frozen=True)
class OutOfCoreMergeResult:
    new_values: np.ndarray | None
    weighted_delta: np.ndarray | None
    output_artifact_ref: dict[str, Any] | None
    lineage_hash: str
    token_weights: dict[str, float]
    metrics: OutOfCoreMergeMetrics
    merge_plan: MergePlan
    numeric_merge_performed: bool
    simulation_only: bool


def build_merge_plan(
    *,
    run_id: str,
    round_id: str,
    fragment_id: int,
    input_artifact_refs: dict[str, dict[str, Any]],
    token_counts: dict[str, int],
    global_values: np.ndarray,
    outer_lr: float,
    chunk_size_bytes: int,
    max_working_bytes: int,
    output_artifact_target: dict[str, Any] | None = None,
    finite_check_policy: str = "require_finite",
) -> MergePlan:
    array = np.asarray(global_values)
    return MergePlan(
        run_id=run_id,
        round_id=round_id,
        fragment_id=fragment_id,
        input_artifact_refs=input_artifact_refs,
        output_artifact_target=output_artifact_target,
        token_weights=normalized_token_weights(token_counts),
        outer_lr=outer_lr,
        dtype=str(array.dtype),
        shape=list(array.shape),
        total_elements=int(array.size),
        chunk_size_bytes=chunk_size_bytes,
        max_working_bytes=max_working_bytes,
        finite_check_policy=finite_check_policy,
    )


def out_of_core_token_weighted_merge(
    *,
    plan: MergePlan,
    global_values: np.ndarray,
    transport: LocalArtifactTransport,
) -> OutOfCoreMergeResult:
    """Merge binary fragment artifacts by reading only one element block at a time."""

    started = time.perf_counter()
    if plan.simulation_only or not plan.numeric_merge_performed:
        return metadata_only_out_of_core_merge(plan=plan)
    global_array = np.asarray(global_values)
    if tuple(plan.shape) != tuple(global_array.shape):
        raise InvariantViolation("merge plan shape does not match global values")
    source_dtype = np.dtype(plan.dtype)
    if source_dtype.kind not in {"f"}:
        raise InvariantViolation("out-of-core merge requires floating point tensors")
    compute_dtype = np.float32 if source_dtype == np.dtype("float16") else source_dtype
    if source_dtype not in {np.dtype("float16"), np.dtype("float32"), np.dtype("float64")}:
        raise InvariantViolation("unsupported out-of-core merge dtype")
    included_refs = {
        learner_id: ref
        for learner_id, ref in plan.input_artifact_refs.items()
        if plan.token_weights.get(learner_id, 0.0) > 0.0
    }
    if not included_refs:
        output = global_array.astype(compute_dtype, copy=True)
        zero_delta = np.zeros_like(output)
        return _finish_result(
            plan=plan,
            output=output.astype(source_dtype, copy=False),
            weighted_delta=zero_delta.astype(source_dtype, copy=False),
            transport=transport,
            metrics=OutOfCoreMergeMetrics(out_of_core_merges=1),
            started=started,
        )
    specs = validate_merge_specs(
        refs=included_refs,
        transport=transport,
        expected_shape=tuple(plan.shape),
        expected_dtype=source_dtype,
    )
    bytes_per_element = source_dtype.itemsize
    minimum_working = bytes_per_element * (len(included_refs) + 3)
    if plan.max_working_bytes < minimum_working:
        raise InvariantViolation("max_working_bytes is too small for one merge element")
    block_elements = max(1, plan.max_working_bytes // minimum_working)
    block_elements = min(block_elements, plan.total_elements)
    global_flat = global_array.reshape(-1).astype(compute_dtype, copy=False)
    output = np.empty(plan.total_elements, dtype=compute_dtype)
    weighted_delta_full = np.empty(plan.total_elements, dtype=compute_dtype)
    blocks = 0
    bytes_read = 0
    peak = 0
    require_finite = plan.finite_check_policy == "require_finite"
    for offset in range(0, plan.total_elements, block_elements):
        count = min(block_elements, plan.total_elements - offset)
        global_block = global_flat[offset : offset + count]
        if require_finite and not np.all(np.isfinite(global_block)):
            raise InvariantViolation("global values contain non-finite values")
        weighted_delta = np.zeros(count, dtype=compute_dtype)
        for learner_id, ref in included_refs.items():
            spec = specs[learner_id]
            byte_offset = spec.byte_offset + offset * bytes_per_element
            byte_length = count * bytes_per_element
            block_bytes = read_ref_range(
                ref=ref,
                transport=transport,
                offset=byte_offset,
                length=byte_length,
            ).data
            learner_block = np.frombuffer(block_bytes, dtype=source_dtype).astype(
                compute_dtype,
                copy=False,
            )
            if require_finite and not np.all(np.isfinite(learner_block)):
                raise InvariantViolation("learner fragment contains non-finite values")
            weighted_delta += plan.token_weights[learner_id] * (learner_block - global_block)
            bytes_read += len(block_bytes)
        output[offset : offset + count] = global_block + plan.outer_lr * weighted_delta
        weighted_delta_full[offset : offset + count] = weighted_delta
        blocks += 1
        peak = max(peak, count * bytes_per_element * (len(included_refs) + 3))
    final_output = output.astype(source_dtype, copy=False).reshape(tuple(plan.shape))
    final_delta = weighted_delta_full.astype(source_dtype, copy=False).reshape(tuple(plan.shape))
    metrics = OutOfCoreMergeMetrics(
        out_of_core_merges=1,
        merge_blocks_processed=blocks,
        merge_input_bytes_read=bytes_read + int(global_array.nbytes),
        merge_output_bytes_written=int(final_output.nbytes),
        merge_peak_working_bytes_estimate=peak,
        merge_wall_time_seconds=time.perf_counter() - started,
    )
    return _finish_result(
        plan=plan,
        output=final_output,
        weighted_delta=final_delta,
        transport=transport,
        metrics=metrics,
        started=started,
    )


def metadata_only_out_of_core_merge(*, plan: MergePlan) -> OutOfCoreMergeResult:
    lineage_hash = sha256_bytes(plan.stable_json().encode("utf-8"))
    return OutOfCoreMergeResult(
        new_values=None,
        weighted_delta=None,
        output_artifact_ref=None,
        lineage_hash=lineage_hash,
        token_weights=plan.token_weights,
        metrics=OutOfCoreMergeMetrics(),
        merge_plan=plan.model_copy(
            update={"numeric_merge_performed": False, "simulation_only": True}
        ),
        numeric_merge_performed=False,
        simulation_only=True,
    )


def _finish_result(
    *,
    plan: MergePlan,
    output: np.ndarray,
    weighted_delta: np.ndarray,
    transport: LocalArtifactTransport,
    metrics: OutOfCoreMergeMetrics,
    started: float,
) -> OutOfCoreMergeResult:
    output_ref = None
    if plan.output_artifact_target is not None:
        target = plan.output_artifact_target
        output_ref = write_tensor_artifact(
            tensors={"global_vector": output},
            run_id=plan.run_id,
            artifact_id=str(target["artifact_id"]),
            artifact_type=str(target.get("artifact_type", "global_vector")),
            transport=transport,
            manifest_path=Path(str(target["manifest_path"])),
            chunk_root=Path(str(target["chunk_root"])),
            chunk_size_bytes=plan.chunk_size_bytes,
            created_by=str(target.get("created_by", "syncer")),
            metadata={
                "global_version": target.get("global_version"),
                "merge_algorithm": "out_of_core_binary_v1",
                "merge_plan_round_id": plan.round_id,
            },
        ).model_dump(mode="json")
    metrics = OutOfCoreMergeMetrics(
        out_of_core_merges=metrics.out_of_core_merges,
        merge_blocks_processed=metrics.merge_blocks_processed,
        merge_input_bytes_read=metrics.merge_input_bytes_read,
        merge_output_bytes_written=metrics.merge_output_bytes_written,
        merge_peak_working_bytes_estimate=metrics.merge_peak_working_bytes_estimate,
        merge_wall_time_seconds=(
            metrics.merge_wall_time_seconds or time.perf_counter() - started
        ),
        merge_rechunk_count=metrics.merge_rechunk_count,
        merge_validation_failures=metrics.merge_validation_failures,
    )
    return OutOfCoreMergeResult(
        new_values=output,
        weighted_delta=weighted_delta,
        output_artifact_ref=output_ref,
        lineage_hash=sha256_bytes(output.tobytes(order="C")),
        token_weights=plan.token_weights,
        metrics=metrics,
        merge_plan=plan,
        numeric_merge_performed=True,
        simulation_only=False,
    )


def estimated_working_bytes(
    *,
    dtype: str,
    block_elements: int,
    learner_count: int,
) -> int:
    return int(np.dtype(dtype).itemsize) * block_elements * (learner_count + 3)


def logical_metadata_merge_plan(
    *,
    run_id: str,
    round_id: str,
    logical_bytes: int,
    max_working_bytes: int,
) -> MergePlan:
    total_elements = max(1, math.ceil(logical_bytes / 4))
    return MergePlan(
        run_id=run_id,
        round_id=round_id,
        fragment_id=0,
        input_artifact_refs={},
        token_weights={},
        outer_lr=1.0,
        dtype="float32",
        shape=[total_elements],
        total_elements=total_elements,
        chunk_size_bytes=1024 * 1024,
        max_working_bytes=max_working_bytes,
        numeric_merge_performed=False,
        simulation_only=True,
        notes=["metadata-only synthetic large-state merge; no numeric ML progress"],
    )
