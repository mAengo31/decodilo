# decodilo

`decodilo` is the first production-oriented scaffold for a Decoupled DiLoCo
training platform. It does not train an LLM, call a cloud API, require GPUs, or
use real credentials. The goal is to make synchronization mechanics,
deterministic replay, and budget gates testable before any cloud rollout.

## Milestone 002 status

Milestone 002 hardens the CPU-only scaffold for correctness and adversarial
testing. It adds explicit invariants, a v1 deterministic event schema, stronger
replay validation, fail-closed pricing lookup, transparent budget arithmetic,
expanded simulation metrics, adversarial simulations, a synchronous baseline,
and machine-readable simulation reports.

Milestone 003 adds a localhost-only multiprocessing runtime with one syncer
process, learner worker subprocesses, JSONL-over-TCP transport envelopes,
idempotent fragment submission, heartbeat timeout handling, process failure
tests, and replay-validated local runtime reports.

Milestone 004 hardens that local runtime with explicit update subscriptions and
acknowledgements, learner version-lag metrics, backpressure limits,
slow/restore chaos controls, learner checkpoints with checksums, retry/reorder
tests, versioned price snapshots, budget manifests, and scaling estimators.

Milestone 005 adds a trainer adapter boundary, numpy convex trainer adapter,
trainer state codec, syncer checkpoint/restart, learner reconnect after syncer
restart, explicit update metric semantics, metric validation, RunSpec,
artifact manifests, and a deterministic local fault matrix.

Milestone 006 adds named-tensor model state flattening and fragmentation, an
optional CPU-capable torch trainer adapter, Lambda cloud dry-run planning,
shape metadata for planning only, scaling estimates inside dry-run reports, and
short local soak runs.

Milestone 007 adds an optional tiny torch causal-LM trainer, safe torch
state/optimizer policy checks, trainer compatibility matrix commands, named
soak profiles, disabled cloud launcher interfaces, launch review checklists,
and dry-run teardown plans.

Milestone 008 prepares for larger-than-toy model state by adding local
content-addressed chunk storage, artifact manifests, streaming artifact
readers/writers, chunked learner/syncer checkpoint artifacts, memory-budget and
spill-to-disk policies, byte-level backpressure, synthetic large-state tests,
streaming merge helpers, preflight gates, and runtime performance counters.

Milestone 009 makes the chunked artifact path a live local runtime path:
learners can submit artifact references, the syncer validates those refs,
streaming chunked merge runs for numeric fragments, global updates can be
delivered as artifact references, replay validates chunked numeric logs against
artifacts, and chunked syncer checkpoints are the primary recovery source in
chunked checkpoint mode.

Milestone 010 adds the `tensor_binary_v1` artifact codec, mmap-friendly local
artifact reading, binary fragment/global-update/checkpoint artifact paths,
binary streaming merge metrics, a local artifact backend interface with a
disabled remote backend stub, and a local overhead/performance harness.

Milestone 011 hardens the binary path with range-oriented artifact access,
backend contract checks, deterministic fault injection, retry metrics,
plan-based out-of-core binary merge, differential merge tests, metadata-only
large-state checks, performance baseline commands, and pytest CI markers.

Milestone 012 adds scalable idempotency records with compaction tombstones,
segmented event logs, replay snapshots, recovery manifests, global-state
lifecycle planning, artifact reachability/GC, run lifecycle CLI commands, and
stricter CI profiles.

Milestone 013 stress-tests lifecycle management across repeated checkpoint,
compact, replay snapshot, recovery-manifest, artifact-audit, and dry-run GC
cycles. It also clarifies GC accounting, adds GC transaction safety, validates
recovery manifest chains, and adds lifecycle-focused CLI commands.

There are still no cloud calls, no Lambda API calls, no credentials, no GPU
requirement, no CUDA/NCCL requirement, no enabled cloud launcher, and no real
LLM trainer.

## Install

```bash
pip install -e '.[dev]'
```

Optional torch adapter tests require an explicit extra:

```bash
pip install -e '.[torch]'
```

## Run tests

```bash
pytest
```

## Run a CPU-only simulation

```bash
python -m decodilo.cli simulate --learners 4 --steps 200 --min-quorum 2 --seed 123
```

The simulator optimizes a toy convex objective, `||W - W_target||^2`, using
independent learner islands and a syncer-side token-weighted merge.

To write a machine-readable run report:

```bash
python -m decodilo.cli simulate \
  --learners 4 \
  --steps 200 \
  --min-quorum 2 \
  --seed 123 \
  --report-json /tmp/decodilo-report.json
```

## Run the local multiprocess runtime

```bash
python -m decodilo.cli local run \
  --learners 4 \
  --steps 200 \
  --min-quorum 2 \
  --seed 123 \
  --workdir /tmp/decodilo-local \
  --report-json /tmp/decodilo-local/report.json
```

This starts a localhost syncer service and learner subprocesses. It writes
`events.jsonl`, learner logs, `syncer_ready.json`, and `report.json` under the
workdir. The report includes replay validation.

Slow/restore chaos is active:

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

Syncer restart is local-only and checkpoint-backed:

```bash
python -m decodilo.cli local run \
  --learners 4 \
  --steps 120 \
  --min-quorum 2 \
  --seed 123 \
  --workdir /tmp/decodilo-local \
  --report-json /tmp/decodilo-local/report.json \
  --syncer-checkpoint-interval-rounds 1 \
  --restart-syncer-after-round 2
```

Validate a report:

```bash
python -m decodilo.cli local validate-report /tmp/decodilo-local/report.json
```

Run a bounded local fault matrix:

```bash
python -m decodilo.cli local fault-matrix \
  --learners 4 \
  --steps 120 \
  --min-quorum 2 \
  --seed 123 \
  --workdir /tmp/decodilo-fault-matrix \
  --cases learner_kill,learner_restart,slow_restore,syncer_restart
```

Run a short local soak:

```bash
python -m decodilo.cli local soak \
  --profile ci \
  --workdir /tmp/decodilo-soak
```

Run with the optional torch causal-LM trainer only after installing the torch
extra:

```bash
python -m decodilo.cli local run \
  --trainer torch_causal_lm \
  --learners 1 \
  --steps 2 \
  --min-quorum 1 \
  --seed 123 \
  --workdir /tmp/decodilo-torch-lm-local \
  --report-json /tmp/decodilo-torch-lm-local/report.json \
  --local-steps-per-sync 1 \
  --fragments 1 \
  --heartbeat-timeout-seconds 2 \
  --trainer-config-json '{"vocab_size":16,"seq_len":4,"batch_size":1,"d_model":4,"num_layers":0,"num_heads":1,"learning_rate":0.05,"device":"cpu"}'
```

Run with explicit memory limits, spill, and chunked checkpoint artifacts:

```bash
python -m decodilo.cli local run \
  --learners 2 \
  --steps 40 \
  --min-quorum 1 \
  --seed 123 \
  --workdir /tmp/decodilo-large-ready \
  --report-json /tmp/decodilo-large-ready/report.json \
  --memory-budget-mb 128 \
  --allow-spill-to-disk \
  --spill-dir /tmp/decodilo-large-ready/spill \
  --chunked-checkpoints
```

Run the live chunked runtime path end to end:

```bash
python -m decodilo.cli local run \
  --learners 2 \
  --steps 40 \
  --min-quorum 1 \
  --seed 123 \
  --workdir /tmp/decodilo-m009-chunked \
  --report-json /tmp/decodilo-m009-chunked/report.json \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --chunk-size-mb 1 \
  --memory-budget-mb 1 \
  --allow-spill-to-disk
```

Run the chunked CI soak profile:

```bash
python -m decodilo.cli local soak \
  --profile chunked_ci \
  --workdir /tmp/decodilo-m009-soak
```

Run the binary chunked runtime path end to end:

```bash
python -m decodilo.cli local run \
  --learners 2 \
  --steps 40 \
  --min-quorum 1 \
  --seed 123 \
  --workdir /tmp/decodilo-m010-binary \
  --report-json /tmp/decodilo-m010-binary/report.json \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --tensor-artifact-codec binary_v1 \
  --fragment-artifact-codec binary_v1 \
  --checkpoint-artifact-codec binary_v1 \
  --chunk-size-mb 1 \
  --memory-budget-mb 1 \
  --allow-spill-to-disk
```

Run the binary chunked CI soak profile:

```bash
python -m decodilo.cli local soak \
  --profile binary_chunked_ci \
  --workdir /tmp/decodilo-m010-soak
```

Run a quick local test profile that excludes integration-heavy, lifecycle,
soak, and perf tests:

```bash
pytest -q -m "not slow and not soak and not perf and not integration and not lifecycle"
```

Measure local binary artifact overhead:

```bash
python -m decodilo.cli perf local-overhead \
  --workdir /tmp/decodilo-m010-perf \
  --trainer numpy_convex \
  --learners 2 \
  --steps 80 \
  --min-quorum 1 \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --tensor-artifact-codec binary_v1 \
  --fragment-artifact-codec binary_v1 \
  --checkpoint-artifact-codec binary_v1 \
  --chunk-size-mb 1 \
  --memory-budget-mb 16 \
  --out /tmp/decodilo-m010-perf/perf_report.json
```

Run targeted performance baselines:

```bash
python -m decodilo.cli perf merge-benchmark \
  --workdir /tmp/decodilo-m011-merge \
  --elements 100000 \
  --learners 4 \
  --chunk-size-kb 64 \
  --dtype float32 \
  --outer-lr 0.7 \
  --out /tmp/decodilo-m011-merge/report.json
```

```bash
python -m decodilo.cli perf artifact-io \
  --workdir /tmp/decodilo-m011-io \
  --total-mb 16 \
  --chunk-size-kb 256 \
  --out /tmp/decodilo-m011-io/report.json
```

```bash
python -m decodilo.cli perf compare-codecs \
  --workdir /tmp/decodilo-m011-codecs \
  --elements 10000 \
  --out /tmp/decodilo-m011-codecs/report.json
```

Run the trainer compatibility matrix:

```bash
python -m decodilo.cli trainer matrix \
  --workdir /tmp/decodilo-trainer-matrix \
  --include-optional
```

## Parse offline Lambda pricing fixture

```bash
python -m decodilo.cli prices lambda --from-fixture tests/fixtures/lambda_pricing_snapshot.html
```

This reads a local HTML fixture only. It does not fetch Lambda pricing and does
not call the Lambda Cloud API.

## Estimate a guarded budget

```bash
python -m decodilo.cli budget estimate \
  --credits 7500 \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --instances 1 \
  --hours 10
```

By default the CLI uses bundled offline sample pricing data. Pass `--price-json`
to use a reviewed local static price file.

Budget output includes the selected provider, GPU type, instance shape,
`price_per_gpu_hour`, `price_per_instance_hour`, total GPUs, planned hours,
base estimated cost, safety buffer, adjusted cost, projected remaining credits,
price source, and whether tax is included. Ambiguous price matches fail closed
unless `--allow-ambiguous-price` is passed explicitly.

## Import a versioned price snapshot

```bash
python -m decodilo.cli prices snapshot import-json \
  --provider lambda \
  --input tests/fixtures/lambda_prices_expected.json \
  --out /tmp/lambda-price-snapshot.json \
  --sample
```

Budget estimates can use snapshots:

```bash
python -m decodilo.cli budget estimate \
  --credits 7500 \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --instances 1 \
  --hours 10 \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --allow-sample-prices
```

Snapshot-backed output includes `snapshot_id` and `record_id`. Sample and stale
snapshots are rejected by default for guarded estimates unless explicitly
allowed.

## Run scaling estimators

```bash
python -m decodilo.cli scaling bandwidth \
  --params 7000000000 \
  --bytes-per-param 2 \
  --learners 8 \
  --fragments 128 \
  --sync-interval-steps 500 \
  --local-step-seconds 1.0 \
  --compression-bits 16
```

```bash
python -m decodilo.cli scaling capacity-plan \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --allow-sample-prices \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --instances 2 \
  --hours 10 \
  --params 7000000000 \
  --bytes-per-param 2 \
  --learners 4 \
  --expected-tokens-per-second 100000 \
  --expected-goodput 0.85 \
  --credits 7500
```

## Create a Lambda cloud dry-run plan

This writes an auditable JSON plan and always reports `launch_allowed=false`.
It does not call Lambda APIs or launch anything.

```bash
python -m decodilo.cli cloud dry-run lambda \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --allow-sample-prices \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --nodes 1 \
  --hours 2 \
  --credits 7500 \
  --max-run-budget 1000 \
  --region us-west-1 \
  --params 7000000000 \
  --bytes-per-param 2 \
  --expected-tokens-per-second 100000 \
  --expected-goodput 0.85 \
  --compression-bits 16 \
  --out /tmp/decodilo-cloud-dry-run.json
```

Validate the dry-run plan:

```bash
python -m decodilo.cli cloud dry-run validate /tmp/decodilo-cloud-dry-run.json
```

Write a launch review checklist. It remains a failed approval gate by default
because real launch is disabled:

```bash
python -m decodilo.cli cloud launch-review \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json \
  --out /tmp/decodilo-launch-review.json
```

Verify the disabled launcher refuses to launch:

```bash
python -m decodilo.cli cloud launch-disabled-test \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json
```

## Inspect and verify chunked artifacts

```bash
python -m decodilo.cli storage inspect-artifact \
  /tmp/decodilo-large-ready/chunked_checkpoints/learner-0.checkpoint.artifact.json
```

```bash
python -m decodilo.cli storage verify-artifact \
  /tmp/decodilo-large-ready/chunked_checkpoints/learner-0.checkpoint.artifact.json
```

If a manifest was moved away from its chunk store, pass the root explicitly:

```bash
python -m decodilo.cli storage verify-artifact \
  /tmp/copied/checkpoint.artifact.json \
  --chunk-root /tmp/decodilo-large-ready/chunked_checkpoints/store
```

## Run preflight checks

Local preflight validates workdir artifacts and report consistency:

```bash
python -m decodilo.cli preflight local \
  --workdir /tmp/decodilo-large-ready \
  --out /tmp/decodilo-large-ready/preflight.json
```

For a live chunked run:

```bash
python -m decodilo.cli preflight local \
  --workdir /tmp/decodilo-m009-chunked \
  --out /tmp/decodilo-m009-chunked/preflight.json
```

Cloud preflight validates a dry-run plan and launch review while keeping launch
disabled:

```bash
python -m decodilo.cli preflight cloud \
  --dry-run-plan /tmp/decodilo-cloud-dry-run.json \
  --workdir /tmp/decodilo-large-ready \
  --out /tmp/decodilo-cloud-preflight.json
```

Cloud preflight output separates `preflight_passed`, `safety_checks_passed`,
`artifact_checks_passed`, `budget_checks_passed`, `launch_review_passed`,
`launch_ready`, and `launch_allowed`. In this build, `launch_ready=false` and
`launch_allowed=false` even when the dry-run safety checks pass.

## Estimate large-state pressure

```bash
python -m decodilo.cli scaling large-state \
  --params 7000000000 \
  --bytes-per-param 2 \
  --optimizer-multiplier 2 \
  --chunk-size-mb 64 \
  --memory-budget-mb 1024 \
  --learners 8
```

The output reports `parameter_count`, `parameter_bytes`,
`optimizer_multiplier`, `optimizer_state_bytes`, `total_state_bytes`,
`chunk_size_bytes`, `estimated_chunk_count`, `memory_budget_bytes`,
`fits_in_memory`, `spill_required`, `learners`, and warnings.

## What is included

- CPU-only learner islands with local step, token, status, throughput, and
  parameter-vector state.
- A syncer with quorum, grace-window, staleness rejection, token-weighted merge,
  and append-only JSONL event logging.
- Deterministic replay of committed sync rounds, rejected update counts, useful
  tokens, and final global vector.
- Offline Lambda pricing parsing from HTML fixtures and static JSON.
- A fail-closed budget guard with safety buffer support.
- Tests for core invariants and failure behavior.
- Replay checks that submitted fragments, useful-token counts, and committed
  vectors agree.
- Adversarial tests for permanent failure, slow learners, quorum loss, stale
  recovery, and zero-token fragments.
- A synchronous baseline for comparing blocking all-learner sync with decoupled
  quorum sync.
- A localhost JSONL-over-TCP transport and local multiprocess runtime.
- Explicit update delivery, update acknowledgements, backpressure accounting,
  learner checkpoint/resume files, and slow/restore chaos controls.
- Versioned price snapshots with provenance and freshness checks.
- Capacity planning estimators for model size, bandwidth, checkpoint storage,
  and cost per useful token.
- A trainer adapter boundary with a numpy convex trainer and stable state codec.
- Syncer checkpoint/restart, learner reconnect, RunSpec, artifact manifests,
  report metric validation, and local fault-matrix testing.
- Named tensor state, deterministic flattening, fragment layout checksums, and
  named-state-backed numpy trainer fragments.
- Optional torch trainer adapter and deterministic synthetic data stream.
- Optional tiny torch causal-LM trainer with safe state export/import and an
  explicit optimizer reset policy.
- Cloud dry-run plans for Lambda with fail-closed price and budget checks.
- Disabled cloud launcher interface, launch review checklist, and dry-run
  teardown plan.
- Local soak runner with named sequential replay-validated runtime profiles.
- Trainer compatibility matrix CLI.
- Local content-addressed chunk store, deterministic artifact manifests, and
  binary-safe artifact verification.
- Memory budget, spill-to-disk policy, byte-level backpressure, chunked
  checkpoint artifacts, streaming merge helpers, synthetic large-state sources,
  preflight gates, and runtime performance counters.
- `tensor_binary_v1` binary tensor artifacts, mmap-friendly artifact reading,
  binary streaming merge metrics, disabled remote artifact backend stubs, and
  a local overhead/performance harness.
- Range-oriented artifact reads, backend contract checks, deterministic
  backend fault injection, retry metrics, and plan-based out-of-core binary
  merge.
- Scalable idempotency records with compaction tombstones, segmented event
  logs, replay snapshots, recovery manifests, global-state lifecycle planning,
  artifact reachability/GC, run lifecycle CLI commands, and stricter CI
  profiles.

## What is intentionally not included

- No production LLM training loop.
- No public network transport or production distributed runtime.
- No real Lambda Cloud API calls.
- No credentials, provider CLIs, enabled cloud launchers, required GPU
  dependencies, CUDA, or NCCL.
- No speculative merge shortcuts that would prevent future distributed
  correctness checks.

See `docs/architecture.md`, `docs/cost_model.md`, `docs/invariants.md`, and
`docs/lambda_rollout_plan.md` for the system boundary and rollout rationale.
See `docs/runtime_hardening.md`, `docs/price_tracker.md`, and
`docs/scaling_model.md` for the Milestone 004 details.
See `docs/large_state_readiness.md`, `docs/chunked_storage.md`,
`docs/streaming_checkpoints.md`, `docs/memory_budgeting.md`, and
`docs/launch_preflight.md` for Milestone 008. See
`docs/live_chunked_runtime.md`, `docs/artifact_transport.md`,
`docs/chunked_recovery.md`, and `docs/streaming_merge.md` for Milestone 009.
See `docs/binary_tensor_artifacts.md`, `docs/artifact_backend_interface.md`,
and `docs/performance_harness.md` for Milestone 010.
See `docs/out_of_core_merge.md`, `docs/artifact_backend_contract.md`,
`docs/fault_injection.md`, `docs/perf_baselines.md`, and
`docs/ci_test_profiles.md` for Milestone 011.
See `docs/idempotency_compaction.md`, `docs/snapshot_replay.md`,
`docs/artifact_retention_gc.md`, `docs/checkpoint_lifecycle.md`, and
`docs/ci_profiles.md` for Milestone 012.
See `docs/lifecycle_stress.md`, `docs/gc_accounting.md`,
`docs/recovery_manifest_chain.md`, and `docs/lifecycle_faults.md` for
Milestone 013.
See `docs/trainer_adapter.md`, `docs/syncer_recovery.md`,
`docs/run_reproducibility.md`, and `docs/metrics_semantics.md` for the
Milestone 005 details.
See `docs/torch_trainer.md`, `docs/model_state_fragmentation.md`,
`docs/cloud_dry_run.md`, and `docs/local_soak.md` for the Milestone 006
details.
See `docs/torch_causal_lm_trainer.md`, `docs/trainer_compatibility_matrix.md`,
`docs/cloud_launcher_safety.md`, and `docs/soak_profiles.md` for the
Milestone 007 details.

## Milestone 012-013 Lifecycle Commands

Inspect and validate a completed local run:

```bash
python -m decodilo.cli run inspect --workdir /tmp/decodilo-run
python -m decodilo.cli run validate --workdir /tmp/decodilo-run
```

Write a replay snapshot, event segments, and a dry-run GC plan:

```bash
python -m decodilo.cli run compact \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-run/compact_report.json
```

Index artifacts and plan or apply garbage collection:

```bash
python -m decodilo.cli artifacts index \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-run/artifact_index.json

python -m decodilo.cli artifacts gc-plan \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-run/gc_plan.json

python -m decodilo.cli artifacts gc \
  --workdir /tmp/decodilo-run \
  --apply \
  --out /tmp/decodilo-run/gc_report.json
```

Audit artifacts, validate recovery chain, and compare genesis replay with
snapshot replay:

```bash
python -m decodilo.cli artifacts audit \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-run/artifact_audit.json

python -m decodilo.cli recovery validate-chain \
  --workdir /tmp/decodilo-run

python -m decodilo.cli replay compare \
  --workdir /tmp/decodilo-run \
  --genesis \
  --snapshot latest
```

Run a short local lifecycle stress cycle:

```bash
python -m decodilo.cli lifecycle stress \
  --workdir /tmp/decodilo-m013-stress \
  --learners 2 \
  --steps 120 \
  --min-quorum 1 \
  --seed 123 \
  --compact-every-rounds 3 \
  --snapshot-every-compactions 2 \
  --gc-plan-every-compactions 2 \
  --out /tmp/decodilo-m013-stress/lifecycle_stress_report.json
```

Quick CI excludes lifecycle, integration-heavy, soak, and perf tests:

```bash
pytest -q -m "not slow and not soak and not perf and not integration and not lifecycle"
```

Cloud launch remains disabled. No Lambda API, credential, GPU, CUDA, or remote
artifact backend exists in this scaffold.
