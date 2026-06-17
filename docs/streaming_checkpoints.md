# Streaming Checkpoints

Milestone 008 keeps the existing small JSON learner and syncer checkpoints, and
adds chunked checkpoint artifact helpers for larger state.

## Chunked Checkpoint Artifacts

Chunked checkpoint helpers write validated checkpoint JSON into the chunk store
and write a storage manifest. The manifest metadata records:

- component type: `learner` or `syncer`
- component id
- checkpoint schema version
- global version
- state reference description

## Restore Validation

Restore reads the manifest, validates every chunk hash, checks total bytes,
decodes the checkpoint JSON, and validates the existing checkpoint checksum.
Missing or corrupted chunks fail closed.

The test suite proves:

- learner chunked checkpoint restore recreates trainer state checksum,
  `local_step`, `tokens_processed`, and global-version fields
- syncer chunked checkpoint restore preserves `global_version`, global vector,
  and idempotency table
- duplicate old fragments remain duplicate after restoring checkpoint state
- corrupted chunks and missing manifests fail restore
- a local syncer restart run with `--chunked-checkpoints` produces
  replay-passing reports and verifiable chunked checkpoint artifacts

## Local Runtime

`local run --chunked-checkpoints` writes chunked checkpoint artifacts alongside
the existing small JSON checkpoints. The artifact manifest includes the retained
chunked checkpoint manifests.

## Milestone 009 Live Recovery

`checkpoint_storage_mode=chunked` makes the chunked syncer checkpoint artifact
the primary live recovery source. In that mode the syncer loads
`live_checkpoints/syncer_checkpoint.artifact.json` and fails closed if it is
missing or corrupt. It must not silently fall back to the inline checkpoint.

`checkpoint_storage_mode=dual` may write both inline and chunked checkpoints,
but the recovery source is explicit in the report and `syncer_recovered` event.

## Current Limits

Checkpoint content is still the existing checkpoint JSON payload inside a
chunked artifact. Future production work should move trainer state, optimizer
state, idempotency tables, and metrics into separate referenced artifacts when
those payloads become large.

## Milestone 010 Binary Tensor Payloads

When `checkpoint_artifact_codec=binary_v1`, numeric tensor payloads referenced
by learner and syncer checkpoints use `tensor_binary_v1`. In
`checkpoint_storage_mode=chunked`, syncer restart treats the chunked checkpoint
artifact as the primary recovery source and validates all binary tensor
artifacts before accepting recovered global state. There is no silent fallback
to inline checkpoint state in chunked mode.
