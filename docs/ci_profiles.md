# CI Profiles

The profile source of truth is `decodilo.runtime.ci_profile_manifest`.
Pytest collection infers profile markers for existing tests so full-suite
coverage is preserved while the quick profile stays intentionally small.

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -o cache_dir=/tmp/decodilo-pytest-cache-full
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" -o cache_dir=/tmp/decodilo-pytest-cache-quick
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "lambda_offline and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-lambda-offline
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "runtime_local and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-runtime-local
```

Optional torch:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_torch_causal_lm_optional.py tests/test_torch_runtime_local_optional.py -q -o cache_dir=/tmp/decodilo-pytest-cache-torch
```

## Marker Policy

- `quick` is opt-in and representative, not a broad "everything not slow" set.
- `lambda_offline` tests may exercise Lambda parsers, reports, fake transports, and fake servers, but must not call real Lambda.
- `lambda_live` and `lambda_real_mutation` are manual-only markers and are excluded from default development profiles.
- `subprocess_heavy` and `runtime_local` identify tests that are valuable in full/runtime shards but are kept out of quick.
- `launch_history_heavy` identifies generated milestone-history tests that remain in full and offline profiles without dominating quick iteration.

The profile report command emits the known profiles, marker expressions,
static marker counts, and warnings:

```bash
python -m decodilo.cli dev ci-profile-report --out /tmp/decodilo-ci-profile-report.json
```
