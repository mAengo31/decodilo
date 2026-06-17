# Chunked Recovery

Milestone 009 makes chunked syncer checkpoints a primary recovery source for
the live local runtime.

## Checkpoint Storage Modes

- `inline`: write and recover from the JSON checkpoint path.
- `chunked`: write and recover from the chunked checkpoint artifact. No silent
  fallback to inline checkpoint is allowed.
- `dual`: write both. Recovery source is explicit in the report and recovery
  event.

## Primary Recovery

When `checkpoint_storage_mode=chunked`, syncer restart loads
`live_checkpoints/syncer_checkpoint.artifact.json` and validates the referenced
chunks before accepting state. Missing or corrupt chunked checkpoints fail
closed.

Recovered state includes run id, global version, global vector, idempotency
table, committed round metadata, learner registry state, metrics snapshot, and
logical time continuity. Duplicate old fragments after recovery must not be
applied again.

## Supervisor Restart Semantics

The local supervisor now requests a clean syncer shutdown before restart so the
syncer writes a current checkpoint before exiting. Termination remains a
fallback if the clean local request fails.

## Event Log

Recovery events include `recovery_source`, `checkpoint_storage_mode`, and the
checkpoint artifact reference when available. Replay rejects impossible version
regressions and validates chunked checkpoint recovery metadata.

## Recovery Manifest

Milestone 012 adds `recovery_manifest.json`. It records the checkpoint ref,
checkpoint storage mode, recovery source, replay snapshot ref when present,
event segment refs, global-state refs, idempotency store ref, required artifact
hashes, and compaction watermarks.

Chunked completed runs are expected to have a valid recovery manifest. Local
preflight fails a chunked completed run when that manifest is missing or
corrupted. The manifest is written atomically and hash-validated.
