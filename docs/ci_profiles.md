# CI Profiles

The full test command remains:

```bash
pytest -q
```

The quick profile skips known long-running integration, lifecycle stress, soak,
and perf tests while keeping core unit, storage, replay, pricing, and protocol
coverage:

```bash
pytest -q -m "not slow and not soak and not perf and not integration and not lifecycle"
```

Focused profiles:

```bash
pytest -q -m "runtime and integration"
pytest -q -m "storage or replay"
pytest -q -m "lifecycle"
pytest -q -m "perf"
pytest -q -m "soak"
```

Marker policy:

- `unit`: pure logic or very small filesystem tests.
- `integration`: subprocesses, TCP transport, or multiple runtime components.
- `runtime`: local multiprocess/runtime behavior.
- `storage`: chunk/artifact storage behavior.
- `replay`: event/replay/snapshot behavior.
- `perf`: timing or throughput harnesses.
- `soak`: sequential soak profiles.
- `lifecycle`: lifecycle stress, compaction, audit, recovery-chain, or GC
  transaction tests.

Use:

```bash
python -m decodilo.cli dev test-profile-summary
```

for the current recommended commands.
