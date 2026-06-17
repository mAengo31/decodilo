# Local Multiprocess Runtime

Milestone 003 runs the same CPU fake-model training through real local process
boundaries:

```text
process 1: syncer service
process 2: learner-0
process 3: learner-1
process 4: learner-2
process 5: learner-3
process 6: supervisor/local runner
```

No cloud APIs, credentials, GPUs, databases, Redis, Ray, Kubernetes, Prometheus,
or external network services are used.

## Syncer Process

The syncer process listens on `127.0.0.1` and wraps the existing `FragmentStore`,
quorum policy, token-weighted merge, event log, replay-compatible commit events,
and metrics.

It handles learner registration, heartbeat updates, fragment submission,
idempotency checks, explicit update subscriptions, update acknowledgements,
backpressure checks, heartbeat timeout detection, syncer checkpointing, recovery,
and shutdown summaries.

## Learner Process

Each learner process connects to the syncer, registers, receives current global
state, calls a `TrainerAdapter`, submits fragments at the configured local
interval, sends heartbeats, and writes a local JSONL log under the workdir. The
default adapter is the numpy convex trainer.

If a learner process is killed, it stops processing tokens because its process
is gone. If restarted with the same learner id, it loads its checkpoint if
present, registers again, receives current global state, reconciles stale
checkpoint versions, and then resumes training. The syncer logs
`learner_recovered` with the current recovery version.

## Update Delivery

Learners call `subscribe_updates` on the existing localhost connection. When the
syncer has a newer committed global version, it returns `global_update_payload`.
The learner applies the vector and sends `global_update_ack`.

The report includes update delivery and version-lag metrics. A learner that
falls too far behind can be treated as stale or unhealthy for quorum decisions.

## Supervisor

The local runner creates the workdir, starts the syncer subprocess, waits for
`syncer_ready.json`, starts learners, monitors child processes, triggers optional
kill/restart/slow/restore chaos after committed round counts, shuts down the
syncer, validates event replay, writes the report, and terminates any remaining
children.

## Workdir Layout

```text
workdir/
  syncer_ready.json
  events.jsonl
  syncer_checkpoint.json
  live_checkpoints/
  artifacts/
  chunks/
  run_spec.json
  artifacts.json
  learner-0.checkpoint.json
  learner-0.control.json
  learner-0.log
  learner-1.log
  learner-2.log
  learner-3.log
  report.json
```

`syncer_ready.json` contains the chosen host, port, and run id. Checkpoint files
are checksum-protected learner state. Control files are supervisor-written local
chaos commands such as slow or restore.

`run_spec.json` is the stable typed run configuration. `artifacts.json` records
artifact paths and hashes for the report, event log, checkpoints, and logs.

In live chunked mode, learner fragments and global updates are exchanged as
local `ArtifactRef` payloads under `artifacts/` and `chunks/`. Event logs record
artifact metadata only.

## Process Failure

Heartbeat timeout uses monotonic wall time in the live runtime. The event log
still records syncer-assigned logical event time. Replay never depends on wall
clock time.

Unhealthy learners are excluded from quorum decisions. If quorum remains met,
the syncer keeps committing. If quorum is not met, rounds are skipped rather than
committed below quorum.

Slow chaos reduces synthetic learner throughput and local step cadence. Restore
returns the learner to baseline speed. Both are logged in learner logs and the
syncer event log.

Backpressure rejections happen before state mutation. They are reported
separately from stale rejections and do not count as useful tokens.

## Syncer Restart

When `--restart-syncer-after-round` is set, the supervisor first requests a
clean local syncer shutdown so the syncer writes a current checkpoint, then
starts a replacement with checkpoint recovery enabled. Termination remains a
fallback if the clean local request fails. The replacement fails closed if the
configured checkpoint source is missing or corrupted.

Learners reconnect by rereading `syncer_ready.json`, re-registering, requesting
current global state, and reconciling version lag before submitting again.

## Cleanup

The local runner terminates any remaining learner or syncer processes in a
`finally` cleanup path. The report records whether orphan cleanup was performed.
