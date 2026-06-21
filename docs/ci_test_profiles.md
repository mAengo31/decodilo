# CI Test Profiles

M048 defines explicit pytest profiles instead of relying on the old broad
negative-marker quick command.

## Canonical Commands

Full suite:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -o cache_dir=/tmp/decodilo-pytest-cache-full
```

Quick development confidence profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" -o cache_dir=/tmp/decodilo-pytest-cache-quick
```

Lambda offline profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "lambda_offline and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-lambda-offline
```

Runtime local profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "runtime_local and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-runtime-local
```

Torch optional profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_torch_causal_lm_optional.py tests/test_torch_runtime_local_optional.py -q -o cache_dir=/tmp/decodilo-pytest-cache-torch
```

## Profile Contract

- `unit`: pure unit tests; no live Lambda, credentials, subprocess-heavy runtime, or torch requirement.
- `quick`: representative development confidence profile. It includes core protocol, replay, storage, pricing, trainer boundary, safety invariants, and representative Lambda offline checks.
- `lambda_offline`: Lambda fixture, fake-server, parser, selector, gate, closeout, and lifecycle-evidence tests. It must not call live Lambda or require credentials.
- `runtime_local`: local multiprocess/runtime tests. It must not call cloud APIs.
- `lifecycle`: longer local lifecycle, GC, replay, compaction, and recovery tests.
- `perf`: benchmark and performance harness tests.
- `torch_optional`: optional torch-only tests when torch is installed.
- `full`: all default tests except manual live credential/operator flows.
- `live_readonly_manual`: manual-only real Lambda read-only tests.
- `real_mutation_manual`: manual-only placeholder; real mutation belongs in CLI/operator flows, not default pytest.

Use the manifest-backed summary and profile report:

```bash
python -m decodilo.cli dev test-profile-summary
python -m decodilo.cli dev ci-profile-report --out /tmp/decodilo-ci-profile-report.json
```

## Classifying New Tests

- Add `pytestmark = pytest.mark.unit` for pure local logic/model/schema tests.
- Add `quick` only for a small representative smoke test that should run on every
  local iteration.
- Add `lambda_offline` for Lambda fixtures, fake clients, parsers, selectors, and
  safety gates that never call the live provider.
- Add `runtime_local` and `subprocess_heavy` for local multiprocess/subprocess
  tests.
- Keep subprocess-sensitive recovery tests out of quick; they belong in
  `runtime_local` and full suite verification.
- Add `lifecycle`, `perf`, `soak`, `hardware_optional`, or `torch_optional` for
  specialized shards.
- Do not add `quick` to live-readonly, real-mutation, subprocess-heavy,
  launch-history-heavy, or broad generated milestone tests.
