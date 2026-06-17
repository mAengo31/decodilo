# Architecture

`decodilo` starts with a CPU simulator because distributed correctness has to be
observable before cloud cost and GPU variance enter the system. The scaffold
models the roles and data contracts a Decoupled DiLoCo platform needs while
keeping the math small enough for deterministic local tests.

## Learner

A learner is an independent local training island. In this milestone it is a
trainer adapter that optimizes local state and reports tokens. The default
adapter is `NumpyConvexTrainer`, which preserves the original convex numpy
objective. Each learner tracks:

- `learner_id`
- `local_step`
- `tokens_processed`
- local parameter vector
- `last_global_version_seen`
- `alive`, `paused`, or `failed` state
- synthetic `throughput_tokens_per_step`

Paused learners stop making progress. Failed learners do not block quorum.

The runtime depends on the `TrainerAdapter` interface rather than the numpy
trainer implementation. A future PyTorch trainer should implement that interface
without changing syncer, transport, replay, or budget protocols.

## Model Fragments

The syncer merge path still operates on flat numeric vectors, but Milestone 006
adds a named tensor state layer at the trainer boundary. Trainers can expose a
state-dict-like mapping of tensor names to arrays, with dtype, shape, offset,
length, and checksums in a tensor manifest. The trainer flattens that state into
fragments suitable for the existing token-weighted merge.

This keeps the syncer trainer-agnostic while allowing future PyTorch adapters to
preserve state-dict semantics.

## Syncer

The syncer owns:

- current global vector and global version
- pending learner updates
- quorum state
- outer optimizer state
- append-only event log
- metrics for accepted updates, rejected updates, useful tokens, rejected
  tokens, and quorum composition

Learner updates arrive asynchronously in logical simulation time. The syncer
rejects failed, zero-token, and stale updates before merge.

## Quorum

`QuorumPolicy` defines:

- `min_quorum`: minimum number of eligible learners required
- `grace_window_ticks`: extra logical ticks after quorum is first reached
- `max_staleness_versions`: maximum tolerated global-version lag
- `allow_partial_round`: whether a grace-expired partial round may commit

With a grace window, the syncer waits after quorum is reached so late learners
can be included. Learners arriving after that window belong to a later round and
do not alter the already committed decision.

## Token-Weighted Merge

For current global vector `W_global`, learner vector `W_i`, and token count
`t_i`, the syncer computes:

```text
delta_i = W_i - W_global
weight_i = t_i / sum(t_i)
weighted_delta = sum(weight_i * delta_i)
W_new = W_global + outer_lr * weighted_delta
```

Zero-token learners have no effect. Stale learners are excluded before merge.
The scaffold includes an SGD-style outer optimizer and typed specs for future
Nesterov and Adam-style outer optimizers.

## Event Log

The event log is deterministic JSONL. Event records use schema `v1` and include:

- `event_id`
- `event_type`
- `schema_version`
- `logical_time`
- `run_id`
- optional `learner_id`
- optional `round_id`
- optional `fragment_id`
- `sequence`
- `payload`

The log is append-only when written to disk. Tests replay the same log and
verify the final global vector and metrics.

`event_id` is deterministic within a run:

```text
{run_id}:{sequence:08d}:{event_type}
```

Serialization uses sorted JSON keys and no wall-clock timestamp.

## Replay

Replay reconstructs enough state for invariants:

- global version sequence
- accepted useful token count
- rejected update count
- rejected token count
- sync round composition
- final global vector

Replay does not execute learner training. It validates the syncer sequence by
tracking submitted fragments, requiring `sync_round_started` before
`sync_round_committed`, checking that accepted learners had pending submissions,
ensuring rejected fragments are not committed, recomputing useful-token counts,
and recomputing the token-weighted merge vector from committed payloads.

Tampered committed vectors, missing submissions, changed accepted-token counts,
unknown schema versions, missing required event fields, and out-of-order logical
time are rejected.

Replay also validates syncer recovery events, learner reconnect events, and
update acknowledgements enough to reject global-version regressions and
impossible future-version references.

## Pricing And Budget Guard

Pricing records are normalized as `PriceProfile` models. Lambda pricing support
can parse a local HTML snapshot or load a static JSON file. Tests use fixtures
only; no network calls occur.

Milestone 004 adds versioned `PriceSnapshot` records with source SHA-256,
source type, parser version, capture time, sample-data flag, and normalized
record ids. Snapshot-backed budget output includes both `snapshot_id` and
`record_id`. Sample and stale snapshots fail closed unless explicitly allowed.

The budget guard tracks starting credits, committed spend, observed spend, and a
safety buffer. It fails closed when a run exceeds `max_run_budget` or projected
remaining credits would go negative.

Price lookup also fails closed when no price matches or when multiple prices
match an ambiguous query. The CLI prints both GPU-hour and instance-hour prices,
the selected shape, total GPUs, planned hours, source URL, source timestamp, and
tax flag.

## Synchronous Baseline

The baseline simulator models blocking all-learner synchronization. Every
learner must be alive and ready for a sync round; a failed learner blocks or
skips that round. The decoupled simulator can continue when quorum is still met.

With all learners healthy and the decoupled quorum set to all learners, the toy
objective should match the synchronous baseline. If decoupled looks better in
that setup, it is a bug or a configuration difference, not proof of training
quality.

## Local Multiprocess Runtime

The single-process simulator remains available. Milestone 003 adds a local
runtime that keeps the same concepts but puts syncer and learners in separate
processes over localhost JSONL-over-TCP.

The syncer process owns quorum, merge, event log, replay-compatible commits, and
heartbeat timeout state. Learner processes own local fake-model training and
submit fragments with idempotency keys. The supervisor starts processes, waits
for the ready file, applies optional kill/restart chaos, shuts the run down, and
writes a replay-validated report.

This runtime is for protocol and process correctness, not ML quality
benchmarking.

Milestone 004 adds explicit update delivery over the same localhost transport.
Learners send `subscribe_updates`; the syncer returns a global update payload
when a newer committed version exists, and learners acknowledge it with
`global_update_ack`. The syncer tracks per-learner acknowledged versions and
reports version-lag metrics.

The syncer also enforces backpressure limits before accepting fragments. A
backpressure rejection is idempotent, does not change global state, and is
accounted separately from stale rejection.

Learners now write checksum-protected checkpoint files and reload them on
restart before requesting current global state. Slow/restore chaos is active
through supervisor-written control files so straggler behavior can be tested
without sleeping for long intervals.

Milestone 005 adds syncer checkpoint/restart. The syncer persists global state,
idempotency, learner registry, update stream state, and metrics. On restart it
loads the checkpoint before accepting learners. Learners reconnect through the
ready file and re-register before resuming.

Local reports now include metric validation, a stable `RunSpec` hash, and an
artifact manifest path.

Milestone 006 keeps the local runtime CPU-only but routes the numpy trainer
through named tensor state. Optional torch trainers can be selected only when
the optional torch dependency is installed.

Milestone 007 adds trainer selection for an optional tiny torch causal-LM
trainer. The runtime still depends on `TrainerAdapter`; the syncer still
receives flat numeric fragments and does not import torch.

Milestone 008 adds local content-addressed chunk storage and chunked checkpoint
artifacts. Small runtime runs still use the existing in-memory numeric merge,
but artifacts and checkpoints can now be written through binary-safe chunk
manifests. The syncer has a chunked fragment-store abstraction for memory,
spill, chunk-store, and metadata-only payload references. Runtime reports
separate replayable logical metrics from non-replayable performance counters
such as wall time, serialized bytes, transport bytes, and spill bytes.

Milestone 009 makes chunked artifacts part of the live local runtime path.
Learners can submit artifact refs, the syncer validates manifests and chunk
hashes before accepting them, numeric streaming chunked merge is available for
accepted fragments, and global updates can be delivered as artifact refs.
Chunked event logs remain metadata-only and replay validates referenced
artifacts for numeric recomputation.

Milestone 010 replaces the chunked runtime's toy JSON numeric artifact path
with `tensor_binary_v1` for trainer fragments, global updates, and checkpoint
tensor payloads when requested. The codec stores raw contiguous tensor bytes in
content-addressed chunks and deterministic manifests with dtype, shape, byte
order, byte ranges, and checksums. The syncer can report binary streaming merge
metrics, learners apply binary global update artifacts before acknowledging,
and the local performance harness measures serialization, artifact I/O, merge,
checkpoint, replay, and update-delivery overhead.

Artifact backends are now abstracted, but only the local filesystem backend is
enabled. The remote backend is a disabled stub that raises on read, write, and
list. No remote storage, Lambda API, cloud credentials, or launch path exists.

## Cloud Dry-Run Planning

Cloud planning is dry-run only. The Lambda planner reads local price snapshots,
checks budget and freshness, selects advisory shape metadata, and writes an
auditable JSON plan with `launch_allowed=false`. It does not call Lambda APIs,
use credentials, or launch resources.

Milestone 007 defines a disabled launcher interface, launch review checklist,
and teardown plan. The interface is intentionally non-operational:
`DisabledCloudLauncher.launch()` raises and real cloud launch remains
impossible.

## Scaling Estimators

Milestone 004 includes deterministic planning calculators for model bytes,
optimizer-state bytes, outer-loop bandwidth, checkpoint storage, cost
projection, and higher-level capacity planning. They are JSON-serializable and
make no cloud calls. The estimates are for reasoning about production scale
before spending credits; they are not ML-quality benchmarks.

## Why CPU Simulator First

CPU simulation gives deterministic, cheap checks for quorum, staleness, replay,
and cost accounting. Those checks are prerequisites for a distributed trainer:
if a failure path or replay invariant is ambiguous locally, adding real GPUs and
cloud lifecycle management makes the system more expensive without making it
more correct.

Milestone 004 still avoids GPUs and cloud execution because the next safe step
is stronger local runtime behavior. The protocol, replay, metrics, checkpoint,
backpressure, and budget contracts should be stable before adding network
failure modes, GPU trainers, or provider lifecycle state.

Milestone 006 still avoids cloud and GPU execution because optional trainer
adapters, named-state fragmentation, dry-run budget plans, and local soak
evidence are prerequisites for a real launcher.

Milestone 008 still avoids cloud and GPU execution because large-state behavior
must first be bounded locally: content hashes must validate, checkpoints must
restore without embedded giant payloads, memory and spill budgets must fail
closed, and preflight must prove that every artifact needed for a future launch
is present and consistent.

Milestone 010 still avoids cloud and GPU execution because the binary artifact
codec, backend boundary, binary merge path, and overhead measurements must be
auditable locally before any GPU trainer or remote artifact backend is safe to
introduce.
