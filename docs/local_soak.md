# Local Soak

Milestone 006 adds a local soak command for longer CPU-only runtime evidence
before any GPU or cloud stage.

Milestone 007 adds named soak profiles so the default run is CI-safe and longer
or torch-backed runs are explicit.

The soak runner executes several local multiprocess cases sequentially,
validates replay and metrics for each report, and writes an aggregate summary.

## CLI

```bash
python -m decodilo.cli local soak \
  --profile ci \
  --workdir /tmp/decodilo-soak
```

`--long` increases the step count for manual local runs. Normal tests use short
CI-safe cases.

Profiles include `ci`, `local_medium`, `local_faulty`, `torch_cpu_ci`, and
`torch_cpu_medium`. Torch profiles require the optional torch extra and remain
CPU-only.

## Summary

`soak_summary.json` includes:

- cases run, passed, and failed
- total committed sync rounds
- total useful tokens
- replay failures
- metric-validation failures
- report artifact paths

## Interpretation

A soak failure means at least one local runtime case failed replay validation,
metric validation, or process cleanup. That must be fixed before introducing
cloud or GPU variables.
