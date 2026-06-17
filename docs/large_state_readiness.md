# Large State Readiness

Milestone 008 prepares `decodilo` for model states larger than toy vectors
without requiring GPUs or cloud execution.

## Why In-Memory Flattening Is Insufficient

The existing syncer can merge small flat vectors in memory. That is useful for
correctness, but production model state can be many gigabytes once parameters,
optimizer state, checkpoints, and learner-local copies are counted. Future
trainers must not assume a full model state can be serialized into one JSON
message or held in memory by the syncer.

## Logical vs Materialized State

`SyntheticLargeStateSource` represents a large logical state by metadata and
deterministic generated chunks. Tests can model a logical 1 GiB state while
materializing only a few KiB. This catches layout, checksum, and artifact
management assumptions without allocating a real large model.

## What Is Ready

- Chunked local artifact storage.
- Content-addressed chunks with SHA-256 validation.
- Synthetic large-state chunk iteration.
- Chunked fragment-store metadata for memory, spill, and metadata-only payloads.
- Streaming merge correctness for small numeric fragments.
- Dry-run metadata lineage for large synthetic fragments.
- Preflight checks that require artifacts, budgets, teardown plans, and disabled
  launch status.

## What Is Not Production-Ready

- The main syncer still performs real numeric merges in memory for small runs.
- No GPU trainer or real distributed PyTorch path exists.
- No remote object store backend exists.
- No Lambda launcher exists.
- Large metadata-only merge is a dry-run lineage check, not a numeric merge.

