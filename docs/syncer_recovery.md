# Syncer Recovery

Milestone 005 adds local syncer checkpoint and restart support. This is still a
localhost-only runtime; no cloud or external storage is used.

## Checkpoint Contents

`syncer_checkpoint.json` includes:

- checkpoint schema version
- run id
- global version and global vector
- outer optimizer state
- fragment store state
- learner registry state
- idempotency table
- committed round state
- explicit pending-round discard policy
- metrics snapshot
- event log offset and last event id
- checksum
- written logical time

## Atomic Writes

Checkpoints are written to a temp file and atomically renamed into place. A
corrupted checksum or unknown schema version is rejected.

## Recovery

When started with recovery enabled, the syncer loads the checkpoint before
accepting learners. It preserves global version, global vector, idempotency
state, metrics, learner registry, and update acknowledgement state.

Pending rounds are currently discarded on recovery. That is conservative: a
future implementation may recover pending rounds only when it can prove they are
safe and replay-compatible.

## Learner Reconnect

Learners that lose the TCP connection reread `syncer_ready.json`, reconnect,
re-register with the same learner id, request current global state, reconcile
version lag, and resume training. The event log records `learner_reconnected`.

## Fail Closed

If recovery is requested and the checkpoint is missing, corrupted, or for a
different run id, the syncer fails closed rather than silently starting a new
run with the same run id.

## Chunked Checkpoint Artifacts

Milestone 008 keeps the existing JSON checkpoint path for tiny local tests and
adds a chunked artifact wrapper for larger checkpoint payloads. The chunked
checkpoint manifest references content-addressed chunks, validates total bytes
and chunk hashes on restore, and records the artifact in the local artifact
manifest when retained.

This does not yet make the live syncer merge fully streaming. It hardens the
checkpoint and artifact boundary so future larger syncer state can be split
into referenced trainer state, optimizer state, idempotency state, and metrics
artifacts.
