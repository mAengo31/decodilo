# Performance Characterization

Milestone 014 adds a stable local-only characterization report for the binary
chunked runtime path. It measures wall-clock overhead with monotonic timers and
keeps replay deterministic: replay never depends on timing fields.

## Command

```bash
python -m decodilo.cli perf characterize \
  --workdir /tmp/decodilo-m014-perf \
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
  --allow-spill-to-disk \
  --out /tmp/decodilo-m014-perf/perf_characterization.json
```

## Report Shape

The report includes environment metadata, trainer and codec modes, logical
metrics, timing, bytes, counters, derived ratios, bottleneck rankings, validation
status, and `cloud_state`.

Timing fields may be `null` when a measurement was not available. They are not
silently converted to zero unless the measured value is truly zero.

The cloud state remains:

```json
{"launch_allowed": false, "launch_ready": false}
```

## Interpretation

Local timing answers which local overhead component dominates on this machine:
training, encoding, artifact I/O, out-of-core merge, update apply, checkpoint,
replay, validation, or GC planning. It is not a cloud performance guarantee.

## Learner-Count Calibration

Milestone 014A adds a local learner-scaling experiment:

```bash
python -m decodilo.cli perf learner-scaling-local \
  --workdir /tmp/decodilo-m014a-learner-local \
  --candidate-learners 1,2,4 \
  --steps 40 \
  --min-quorum-ratio 0.5 \
  --trainer numpy_convex \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --fragment-artifact-codec binary_v1 \
  --tensor-artifact-codec binary_v1 \
  --checkpoint-artifact-codec binary_v1 \
  --out /tmp/decodilo-m014a-learner-local/report.json
```

The report records observed useful tokens per second, artifact bytes, merge
time, checkpoint time, replay time, and process overhead per learner count. It
is calibration data for planning only.
