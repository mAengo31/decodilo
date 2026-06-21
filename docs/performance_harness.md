# Performance Harness

Milestone 010 adds a local overhead harness for measuring the CPU-only runtime
cost of serialization, chunking, artifact I/O, streaming merge, checkpoints,
replay, and update delivery.

## Command

```bash
python -m decodilo.cli perf local-overhead \
  --workdir /tmp/decodilo-m010-perf \
  --trainer numpy_convex \
  --learners 2 \
  --steps 80 \
  --min-quorum 1 \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --tensor-artifact-codec binary_v1 \
  --fragment-artifact-codec binary_v1 \
  --checkpoint-artifact-codec binary_v1 \
  --chunk-size-mb 1 \
  --memory-budget-mb 16 \
  --out /tmp/decodilo-m010-perf/perf_report.json
```

## Report

The report is stable JSON and includes run config, codec modes, logical
training/sync metrics, runtime perf counters, artifact metrics, merge metrics,
checkpoint metrics, replay metrics, overhead breakdown, derived ratios,
validation results, and warnings.

The timing fields use monotonic wall time. Replay does not depend on wall time,
and tests assert only that fields exist and are nonnegative.

## Interpretation

This harness is for local overhead and regression tracking. It does not predict
GPU throughput, WAN bandwidth, or cloud pricing by itself. Use it before
GPU/cloud experiments to identify whether tensor encoding, artifact writes,
streaming merge, or checkpointing dominate the local runtime.

Milestone 011 adds `perf merge-benchmark`, `perf artifact-io`, and
`perf compare-codecs` for smaller targeted baselines. See
`docs/perf_baselines.md`.

Milestone 014 adds `perf characterize` for the stable
`PerformanceCharacterizationReport`, `perf matrix` for small scaling grids, and
`perf check-budget` for explicit overhead thresholds. See
`docs/performance_characterization.md` and `docs/overhead_budget.md`.
