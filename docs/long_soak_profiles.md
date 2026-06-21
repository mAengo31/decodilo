# Long Soak Profiles

Milestone 014 adds longer soak profile definitions while keeping default CI
profiles short.

Profiles:

- `lifecycle_ci`: short lifecycle compaction/snapshot validation.
- `binary_perf_ci`: short binary chunked runtime plus perf characterization.
- `local_long_lifecycle`: longer lifecycle soak; requires `--long`.
- `local_long_binary`: longer binary chunked soak; requires `--long`.
- `torch_cpu_perf_ci`: reserved for optional torch CPU timing when torch is
  installed.

Examples:

```bash
python -m decodilo.cli local soak \
  --profile lifecycle_ci \
  --workdir /tmp/decodilo-m014-lifecycle-ci
```

```bash
python -m decodilo.cli local soak \
  --profile local_long_lifecycle \
  --workdir /tmp/decodilo-m014-long \
  --long
```

Long profiles refuse to run without `--long` so a CI or local shell typo does
not start a larger run accidentally.

