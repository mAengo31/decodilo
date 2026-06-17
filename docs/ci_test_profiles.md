# CI Test Profiles

Milestone 012 tightens pytest markers so the quick profile is materially
smaller than the full suite.

## Markers

- `unit`: fast isolated tests
- `integration`: subprocess or multi-component tests
- `slow`: longer runtime or stress tests
- `soak`: local soak profile tests
- `perf`: local performance baseline tests
- `torch_optional`: optional torch tests
- `cloud_disabled`: tests proving cloud launch remains disabled
- `storage`: chunk/artifact storage tests
- `replay`: event replay and snapshot replay tests
- `runtime`: local runtime tests
- `lifecycle`: lifecycle stress, compaction, recovery-chain, audit, and GC
  transaction tests

## Commands

Full suite:

```bash
pytest -q
```

Quick suite:

```bash
pytest -q -m "not slow and not soak and not perf and not integration and not lifecycle"
```

Soak tests:

```bash
pytest -q -m "soak"
```

Perf tests:

```bash
pytest -q -m "perf"
```

The full acceptance suite still runs every marker. The quick command is for
fast local iteration and CI shards.

Runtime integration shard:

```bash
pytest -q -m "runtime and integration"
```

Storage/replay shard:

```bash
pytest -q -m "storage or replay"
```

Lifecycle shard:

```bash
pytest -q -m "lifecycle"
```

Current command summary:

```bash
python -m decodilo.cli dev test-profile-summary
```
