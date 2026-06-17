# Checkpoint Lifecycle

Checkpoint lifecycle policy controls how many syncer and learner checkpoints remain
protected:

- `keep_latest_n_syncer_checkpoints`
- `keep_latest_n_learner_checkpoints`
- `checkpoint_every_n_rounds`
- `snapshot_every_n_checkpoints`

Old checkpoints become GC-eligible only when they are not referenced by the latest recovery
manifest, replay snapshot, or retention policy. The latest syncer checkpoint remains the
recovery checkpoint.

In chunked mode, recovery manifests point to the chunked checkpoint artifact. Missing or
corrupted recovery inputs fail closed; the runtime must not silently start a new run with
the same run id.

