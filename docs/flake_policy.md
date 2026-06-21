# Flake Policy

Flakes are not ignored silently.

Allowed resolutions:

- make the test deterministic
- mark subprocess-sensitive tests as `subprocess_heavy` or `integration`
- use bounded retry only in an explicit test helper with reporting

Disallowed resolutions:

- ignore without tracking
- hide failures by broad deselection
- remove safety coverage from the full suite

The quick profile excludes `subprocess_heavy` tests so local iteration remains
fast while the full suite keeps the coverage.

## Subprocess Recovery Tests

`tests/test_local_process_failure.py::test_local_recovery_after_kill` is
`runtime_local` and `subprocess_heavy`, so it stays out of quick while remaining
in full and runtime-local profiles.

Subprocess-sensitive recovery tests should prefer event-driven assertions over
sleep-based timing. For learner recovery, the test restarts the learner in the
same deterministic recovery window as the kill trigger and asserts a committed
event whose sequence is after the recovery event.

Bounded retry is allowed only as an opt-in helper for subprocess-heavy tests. If
used, it must report attempts, the first failure summary, final result, and the
reason. Repeated failure must still fail the test.

Policy report:

```bash
python -m decodilo.cli dev flake-policy --out /tmp/decodilo-flake-policy.json
```
