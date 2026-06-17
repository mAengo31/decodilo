"""Small local performance baseline commands."""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.tensor_artifact import write_tensor_artifact
from decodilo.syncer.out_of_core_merge import build_merge_plan, out_of_core_token_weighted_merge
from decodilo.syncer.token_weighted_merge import LearnerDelta, token_weighted_merge
from decodilo.trainer.fragment_artifacts import write_fragment_artifact
from decodilo.trainer.state_codec import make_fragment
from decodilo.trainer.torch_optional import torch_available


def environment_summary() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_available": torch_available(),
    }


def write_report(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_merge_benchmark(
    *,
    workdir: str | Path,
    elements: int,
    learners: int,
    chunk_size_kb: int,
    dtype: str,
    outer_lr: float,
    out: str | Path,
) -> dict[str, Any]:
    root = Path(workdir)
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(workdir=str(root), artifact_root=str(root / "artifacts"))
    )
    rng = np.random.default_rng(123)
    np_dtype = np.dtype(dtype)
    global_values = rng.normal(size=elements).astype(np_dtype)
    refs: dict[str, dict[str, Any]] = {}
    deltas: list[LearnerDelta] = []
    tokens: dict[str, int] = {}
    started = time.perf_counter()
    for index in range(learners):
        learner_id = f"learner-{index}"
        values = rng.normal(size=elements).astype(np_dtype)
        token_count = index + 1
        ref = write_tensor_artifact(
            tensors={"fragment": values},
            run_id="perf-merge",
            artifact_id=f"perf-merge:{learner_id}:fragment",
            artifact_type="trainer_fragment",
            transport=transport,
            manifest_path=root / "artifacts" / f"{learner_id}.artifact.json",
            chunk_root=root / "artifacts" / "store",
            chunk_size_bytes=chunk_size_kb * 1024,
            created_by=learner_id,
            metadata={
                "fragment_id": 0,
                "global_version": 0,
                "tokens": token_count,
                "learner_id": learner_id,
                "dtype": str(values.dtype),
                "shape": list(values.shape),
            },
        )
        refs[learner_id] = ref.model_dump(mode="json")
        deltas.append(LearnerDelta(learner_id, values.astype(np.float64), token_count, 0))
        tokens[learner_id] = token_count
    plan = build_merge_plan(
        run_id="perf-merge",
        round_id="round-1",
        fragment_id=0,
        input_artifact_refs=refs,
        token_counts=tokens,
        global_values=global_values,
        outer_lr=outer_lr,
        chunk_size_bytes=chunk_size_kb * 1024,
        max_working_bytes=max(chunk_size_kb * 1024, np_dtype.itemsize * (learners + 3)),
    )
    merged = out_of_core_token_weighted_merge(
        plan=plan,
        global_values=global_values,
        transport=transport,
    )
    memory = token_weighted_merge(global_values.astype(np.float64), deltas)
    validation_passed = np.allclose(
        merged.new_values,
        global_values + outer_lr * (memory.new_global_vector - global_values),
        rtol=1e-5,
        atol=1e-6,
    )
    wall_time = time.perf_counter() - started
    report = {
        "config": {
            "elements": elements,
            "learners": learners,
            "chunk_size_kb": chunk_size_kb,
            "dtype": dtype,
            "outer_lr": outer_lr,
        },
        "environment": environment_summary(),
        "wall_time_seconds": wall_time,
        "bytes_read": merged.metrics.merge_input_bytes_read,
        "bytes_written": merged.metrics.merge_output_bytes_written,
        "throughput_bytes_per_second": _throughput(
            merged.metrics.merge_input_bytes_read + merged.metrics.merge_output_bytes_written,
            wall_time,
        ),
        "validation_passed": bool(validation_passed),
        "warnings": [],
    }
    write_report(out, report)
    return report


def run_artifact_io_baseline(
    *,
    workdir: str | Path,
    total_mb: int,
    chunk_size_kb: int,
    out: str | Path,
) -> dict[str, Any]:
    root = Path(workdir)
    store = ChunkStore(root / "store")
    data = bytes(index % 251 for index in range(total_mb * 1024 * 1024))
    started = time.perf_counter()
    manifest = write_binary_artifact(
        store=store,
        data=data,
        artifact_id="artifact-io",
        artifact_type="perf",
        run_id="perf-io",
        chunk_size_bytes=chunk_size_kb * 1024,
        manifest_path=root / "artifact.artifact.json",
    )
    read_back = store.read_bytes(manifest)
    wall_time = time.perf_counter() - started
    report = {
        "config": {"total_mb": total_mb, "chunk_size_kb": chunk_size_kb},
        "environment": environment_summary(),
        "wall_time_seconds": wall_time,
        "bytes_read": len(read_back),
        "bytes_written": len(data),
        "throughput_bytes_per_second": _throughput(len(data) + len(read_back), wall_time),
        "validation_passed": read_back == data,
        "warnings": [],
    }
    write_report(out, report)
    return report


def run_compare_codecs(
    *,
    workdir: str | Path,
    elements: int,
    out: str | Path,
) -> dict[str, Any]:
    root = Path(workdir)
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(workdir=str(root), artifact_root=str(root / "artifacts"))
    )
    values = np.linspace(0.0, 1.0, elements, dtype=np.float64)
    fragment = make_fragment(
        trainer_type="numpy_convex",
        run_id="perf-codecs",
        learner_id="learner-0",
        fragment_id=0,
        global_version=0,
        data=values,
        tokens=1,
    )
    started = time.perf_counter()
    json_ref = write_fragment_artifact(
        fragment=fragment,
        transport=transport,
        manifest_path=root / "artifacts" / "json.artifact.json",
        chunk_root=root / "artifacts" / "json-store",
        chunk_size_bytes=64 * 1024,
        created_by="learner-0",
        codec="json_safe",
    )
    binary_ref = write_fragment_artifact(
        fragment=fragment,
        transport=transport,
        manifest_path=root / "artifacts" / "binary.artifact.json",
        chunk_root=root / "artifacts" / "binary-store",
        chunk_size_bytes=64 * 1024,
        created_by="learner-0",
        codec="binary_v1",
    )
    wall_time = time.perf_counter() - started
    report = {
        "config": {"elements": elements},
        "environment": environment_summary(),
        "wall_time_seconds": wall_time,
        "bytes_read": 0,
        "bytes_written": json_ref.total_bytes + binary_ref.total_bytes,
        "json_safe_bytes": json_ref.total_bytes,
        "binary_v1_bytes": binary_ref.total_bytes,
        "throughput_bytes_per_second": _throughput(
            json_ref.total_bytes + binary_ref.total_bytes,
            wall_time,
        ),
        "validation_passed": binary_ref.total_bytes > 0 and json_ref.total_bytes > 0,
        "warnings": [],
    }
    write_report(out, report)
    return report


def _throughput(byte_count: int, seconds: float) -> float:
    return float(byte_count) / seconds if seconds > 0 else 0.0
