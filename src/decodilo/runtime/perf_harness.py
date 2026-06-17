"""Local overhead/performance harness."""

from __future__ import annotations

import time
from pathlib import Path

from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner
from decodilo.runtime.overhead import safe_fraction, useful_tokens_per_second
from decodilo.runtime.perf_reports import PerfOverheadReport, write_perf_report


def run_local_overhead_harness(
    *,
    config: LocalRunConfig,
    out: str | Path,
) -> PerfOverheadReport:
    started = time.perf_counter()
    report = LocalRunner(config).run()
    total_wall = time.perf_counter() - started
    metrics = dict(report.metrics)
    perf = dict(report.perf_counters)
    artifact_metrics = {
        key: metrics.get(key, 0)
        for key in (
            "chunked_fragment_submissions",
            "artifact_ref_validations",
            "artifact_ref_validation_failures",
            "chunked_fragment_bytes_accepted",
            "artifact_bytes_read",
            "artifact_chunks_read",
            "binary_global_update_bytes_sent",
        )
    }
    merge_metrics = {
        key: metrics.get(key, 0)
        for key in (
            "live_streaming_merges",
            "live_streaming_merge_bytes_read",
            "live_streaming_merge_bytes_written",
            "binary_streaming_merges",
            "binary_streaming_merge_bytes_read",
            "binary_streaming_merge_bytes_written",
            "binary_streaming_merge_chunks_read",
            "binary_streaming_merge_chunks_written",
        )
    }
    checkpoint_metrics = {
        "checkpoint_storage_mode": config.checkpoint_storage_mode,
        "checkpoint_artifact_codec": config.checkpoint_artifact_codec,
    }
    breakdown = {
        "train_wall_time_seconds": 0.0,
        "fragment_encode_wall_time_seconds": 0.0,
        "artifact_write_wall_time_seconds": float(
            perf.get("artifact_write_wall_time_seconds", 0.0)
        ),
        "artifact_read_wall_time_seconds": float(metrics.get("artifact_validation_seconds", 0.0)),
        "merge_wall_time_seconds": float(
            metrics.get("binary_streaming_merge_wall_time_seconds", 0.0)
        ),
        "update_decode_apply_wall_time_seconds": 0.0,
        "checkpoint_wall_time_seconds": float(perf.get("syncer_checkpoint_wall_time_seconds", 0.0)),
        "replay_wall_time_seconds": 0.0,
        "total_wall_time_seconds": total_wall,
    }
    useful_tokens = int(metrics.get("useful_tokens_accepted", 0))
    artifact_bytes = int(artifact_metrics.get("chunked_fragment_bytes_accepted", 0))
    derived = {
        "encode_time_fraction": safe_fraction(
            breakdown["fragment_encode_wall_time_seconds"],
            total_wall,
        ),
        "merge_time_fraction": safe_fraction(breakdown["merge_wall_time_seconds"], total_wall),
        "checkpoint_time_fraction": safe_fraction(
            breakdown["checkpoint_wall_time_seconds"],
            total_wall,
        ),
        "artifact_io_time_fraction": safe_fraction(
            breakdown["artifact_write_wall_time_seconds"]
            + breakdown["artifact_read_wall_time_seconds"],
            total_wall,
        ),
        "useful_tokens_per_second": useful_tokens_per_second(useful_tokens, total_wall),
        "artifact_bytes_per_useful_token": (
            float(artifact_bytes) / useful_tokens if useful_tokens else 0.0
        ),
        "merge_bytes_per_second": (
            float(merge_metrics.get("binary_streaming_merge_bytes_read", 0))
            / total_wall
            if total_wall > 0
            else 0.0
        ),
    }
    perf_report = PerfOverheadReport(
        run_id=report.run_id,
        config=report.config,
        trainer_type=report.trainer_type,
        codec_modes={
            "tensor_artifact_codec": config.tensor_artifact_codec,
            "fragment_artifact_codec": config.fragment_artifact_codec,
            "checkpoint_artifact_codec": config.checkpoint_artifact_codec,
        },
        logical_metrics=metrics,
        runtime_perf_counters=perf,
        artifact_metrics=artifact_metrics,
        merge_metrics=merge_metrics,
        checkpoint_metrics=checkpoint_metrics,
        replay_metrics=report.replay_validation.model_dump(mode="json"),
        overhead_breakdown=breakdown,
        derived_ratios=derived,
        validation={
            "replay_passed": report.replay_validation.replay_passed,
            "metric_validation_passed": bool(report.metric_validation.get("passed")),
            "artifact_validation_passed": bool(report.artifact_manifest_path),
        },
        warnings=[],
    )
    write_perf_report(out, perf_report)
    return perf_report
