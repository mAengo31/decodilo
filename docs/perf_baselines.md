# Performance Baselines

Milestone 011 adds short local baseline commands. They are not GPU or cloud
benchmarks.

## Merge Benchmark

```bash
python -m decodilo.cli perf merge-benchmark \
  --workdir /tmp/decodilo-m011-merge \
  --elements 100000 \
  --learners 4 \
  --chunk-size-kb 64 \
  --dtype float32 \
  --outer-lr 0.7 \
  --out /tmp/decodilo-m011-merge/report.json
```

## Artifact I/O

```bash
python -m decodilo.cli perf artifact-io \
  --workdir /tmp/decodilo-m011-io \
  --total-mb 16 \
  --chunk-size-kb 256 \
  --out /tmp/decodilo-m011-io/report.json
```

## Compare Codecs

```bash
python -m decodilo.cli perf compare-codecs \
  --workdir /tmp/decodilo-m011-codecs \
  --elements 10000 \
  --out /tmp/decodilo-m011-codecs/report.json
```

Reports include config, environment summary, wall time, bytes read/written,
throughput estimates, validation status, and warnings.

Do not overinterpret local timing. These commands are for regression and rough
overhead comparisons only.

For matrix-style characterization across learner count, element count, and
chunk size, use:

```bash
python -m decodilo.cli perf matrix \
  --workdir /tmp/decodilo-m014-perf-matrix \
  --trainer numpy_convex \
  --learners 1,2,4 \
  --elements 1024,8192 \
  --chunk-size-kb 64,256 \
  --steps 40 \
  --min-quorum 1 \
  --codec binary_v1 \
  --out /tmp/decodilo-m014-perf-matrix/matrix.json
```
