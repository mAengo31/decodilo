# Quick Test Profile

The quick profile is the default development confidence suite:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" -o cache_dir=/tmp/decodilo-pytest-cache-quick
```

It includes representative tests for:

- core retry, storage, replay, pricing, and budget logic
- trainer interface and state codec boundaries
- Lambda mutation guard and no-live-call invariants
- response capture/error handling
- lifecycle-smoke success evidence
- selector and execution-gate smoke checks
- CI profile and flake policy guards

It intentionally excludes subprocess-heavy runtime tests, lifecycle stress,
performance harnesses, optional hardware/torch tests, live Lambda tests, and any
real mutation profile. It also excludes `launch_history_heavy` so repeated
milestone-history checks remain in full and Lambda offline profiles without
slowing normal iteration.

`test_local_recovery_after_kill` is intentionally excluded because it exercises
subprocess kill/restart recovery. It belongs to `runtime_local` and
`subprocess_heavy`, not quick.

Add `quick` only when the test is a representative, deterministic smoke check.
Do not mark entire feature families as quick by default.
