# Soak Profiles

Milestone 007 adds named local soak profiles. Profiles make soak runs
reproducible and keep the default profile CI-safe.

## Profiles

- `ci`: short numpy runtime cases for normal verification.
- `local_medium`: longer local run for manual evidence.
- `local_faulty`: fault-heavy local process cases.
- `torch_cpu_ci`: short optional torch causal-LM run when torch is installed.
- `torch_cpu_medium`: longer optional torch CPU run.

Optional torch profiles are skipped by policy when torch is not installed.

## CLI

Default CI-safe profile:

```bash
python -m decodilo.cli local soak \
  --profile ci \
  --workdir /tmp/decodilo-soak
```

Optional torch CPU profile:

```bash
python -m decodilo.cli local soak \
  --profile torch_cpu_ci \
  --trainer torch_causal_lm \
  --workdir /tmp/decodilo-soak-torch \
  --trainer-config-json '{"vocab_size":16,"seq_len":4,"batch_size":1,"d_model":4,"num_layers":0,"num_heads":1,"learning_rate":0.05,"device":"cpu"}'
```

Explicit CLI flags override profile defaults. `--long` increases step counts
for manual local runs and is not required for CI.

## Summary

`soak_summary.json` includes profile, trainer, cases run, pass/fail counts,
replay failures, metric validation failures, total committed rounds, total
useful tokens, total wall time, and report artifact paths.

## Interpretation

A soak failure means at least one case failed replay validation, metric
validation, or process cleanup. That must be fixed locally before any GPU or
cloud stage.

