# Runtime Hardening

Milestone 004 keeps the runtime local and CPU-only, but hardens the process
boundary so later GPU and cloud work inherits tested distributed-systems
behavior.

Milestone 005 adds trainer adapters, syncer restart/recovery, RunSpec,
artifact manifests, and report metric validation.

## Update Delivery

Learners now use an explicit update subscription path over the existing
localhost JSONL connection. A learner sends `subscribe_updates` with its last
applied global version. The syncer either returns `global_update_payload` when a
new committed version is available or `subscribe_updates_ack` after a short
timeout.

Learners acknowledge applied versions with `global_update_ack`. The syncer
tracks each learner's latest acknowledged global version and reports version-lag
metrics:

- `global_update_broadcasts`
- `global_update_messages_sent`
- `global_update_acks`
- `duplicate_global_update_acks`
- `missing_global_update_acks`
- `learner_update_lag_current`
- `learner_update_lag_max`
- `learner_update_lag_avg`
- `stale_due_to_lag_count`

Replay does not model delivery timing, but it rejects update delivery events
that reference future global versions.

## Backpressure

The syncer applies bounded submission accounting before accepting fragments:

- max pending messages per learner
- max pending fragments per learner
- max inflight bytes per learner
- max total inflight bytes

Fragments rejected by backpressure do not affect the global vector and do not
count as useful tokens. Duplicate submissions remain idempotent even when the
original outcome was a backpressure rejection.

## Slow And Restore Chaos

The local runner can slow and restore a learner after committed round counts:

```bash
python -m decodilo.cli local run \
  --learners 4 \
  --steps 200 \
  --min-quorum 2 \
  --seed 123 \
  --workdir /tmp/decodilo-local \
  --report-json /tmp/decodilo-local/report.json \
  --slow-learner learner-1:factor=0.25:after-round=2 \
  --restore-learner learner-1:after-round=5
```

Slow control reduces synthetic throughput and local step cadence. Restore
returns the learner to its baseline speed. The syncer logs `learner_slowed` and
`learner_speed_restored`.

## Learner Checkpoint And Resume

Learner checkpoints are versioned JSON files written atomically through a temp
file and rename. The checkpoint includes local step, token counts, global
versions, synthetic throughput, the trainer payload, and a checksum over the
payload.

A restarted learner with the same learner id loads its checkpoint, registers
with the syncer, requests current global state, reconciles any stale checkpoint
version, and only then resumes local training.

## Retry And Reorder Harness

Retry/reorder tests cover duplicate submissions, delayed or reordered messages,
duplicate acknowledgements, malformed envelopes, and reconnecting learners.

## Live Chunked Payloads

Milestone 009 adds live chunked payload delivery. Learners may submit
`ArtifactRef` payloads instead of inline vectors, and the syncer validates
manifest hashes, chunk hashes, run id, total bytes, and path safety before
acceptance. Global updates can also be delivered as artifact refs and are
acknowledged only after the learner applies them.

The transport remains localhost JSONL plus local shared filesystem artifacts.
There is no remote artifact backend and no cloud object-store integration.

Tests cover duplicate fragments, duplicate update acknowledgements, reordered
heartbeat/fragment messages, malformed messages during an active run, and
reconnect with the same learner id. These cases must not corrupt health state,
double-count tokens, or break replay.

## Syncer Checkpoint And Restart

The syncer writes checksum-protected checkpoints containing global state,
idempotency, learner registry, update-stream state, metrics, and event-log
position. A restarted syncer must load this checkpoint before accepting learners
and must not regress `global_version`.

Learners reconnect through the ready file, re-register, request current global
state, and resume through the trainer adapter.

## Why Before GPU Or Cloud

Real GPU trainers and cloud launchers add cost, nondeterminism, and larger blast
radius. Backpressure, idempotency, checkpoint recovery, update acknowledgements,
and replay validation are prerequisites that can be proven on localhost first.

## Milestone 008 Runtime Limits

Runtime backpressure now distinguishes message-count pressure, byte pressure,
memory-budget pressure, and spill-budget pressure. Fragment submissions carry
declared payload bytes, and size mismatches are rejected before global state
mutation.

Local reports include performance counters for wall time, serialization bytes,
transport bytes, merge/checkpoint timing fields, and spill bytes. These counters
are diagnostic only; replay continues to depend only on deterministic logical
events.
