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

Milestone 014 characterizes local runtime overhead with stable performance
reports, perf matrices, overhead budgets, longer guarded soak profiles,
resumable GC trash cleanup, reachability graph reports, and optional
single-device hardware probes. Cloud launch remains impossible.

Milestone 014A adds local-only learner-pod scaling planning. It models fixed
total compute, expanding compute, and scavenged learner pods; estimates failure
goodput, quorum/grace tradeoffs, artifact/backend pressure, bandwidth pressure,
syncer pressure, heuristic algorithmic efficiency, and pod cost; emits backend
design targets for future remote artifact planning; and provides a local
learner-scaling experiment for calibration. Cloud launch remains impossible.

Milestone 015 validates future remote artifact backend requirements without
implementing any real remote backend. It adds requirement models, a disabled
remote backend contract, a local remote-backend simulator, security/lifecycle
checks, manual cost estimates, design validation reports, and preflight evidence
gates. No remote backend is enabled and cloud launch remains impossible.

Milestones 018 and 019 define the Lambda Cloud API boundary. M018 is fully
offline with fake fixtures. M019 adds opt-in read-only live discovery, and
M019A/M019C calibrate endpoint coverage, response shapes, pagination limits,
redaction, live ledger warnings, optional unsupported endpoint handling, and
read-only preflight behavior. Lambda launch and mutation remain impossible.

Default tests and default commands still perform no cloud calls, use no Lambda
credentials, require no GPU, and require no CUDA/NCCL. The only command allowed
to call Lambda is the explicit opt-in read-only `lambda live-discover` command;
it uses GET allowlisted endpoints only and cannot launch or mutate resources.

## Install

```bash
pip install -e '.[dev]'
```

Optional torch adapter tests require an explicit extra:

```bash
pip install -e '.[torch]'
```

## Learner-pod scaling planning

```bash
python -m decodilo.cli scaling learner-sweep \
  --mode fixed_total_compute \
  --total-gpus 64 \
  --candidate-learners 1,2,4,8,16 \
  --per-gpu-token-rate 1000 \
  --failure-rate-per-hour 0.02 \
  --recovery-time-seconds 300 \
  --training-duration-hours 24 \
  --model-params 7000000000 \
  --bytes-per-param 2 \
  --fragment-count 128 \
  --chunk-size-mb 64 \
  --sync-interval-steps 500 \
  --local-step-seconds 1.0 \
  --bandwidth-cap-gbps 10 \
  --artifact-read-gbps 20 \
  --artifact-write-gbps 10 \
  --syncer-merge-gbps 5 \
  --out /tmp/decodilo-learner-sweep.json
```

```bash
python -m decodilo.cli scaling optimize-pods \
  --scenario-json /tmp/decodilo-scenario.json \
  --objective minimize_cost_per_adjusted_token \
  --out /tmp/decodilo-pod-optimization.json
```

```bash
python -m decodilo.cli scaling quorum-grace-sweep \
  --learners 8 \
  --quorum-candidates 2,4,6,8 \
  --grace-window-seconds 0,1,5,10 \
  --failure-rate-per-hour 0.02 \
  --speed-variance 0.2 \
  --out /tmp/decodilo-quorum-grace.json
```

```bash
python -m decodilo.cli scaling backend-targets \
  --scaling-report /tmp/decodilo-pod-optimization.json \
  --out /tmp/decodilo-backend-targets.json
```

```bash
python -m decodilo.cli perf learner-scaling-local \
  --workdir /tmp/decodilo-m014a-learner-local \
  --candidate-learners 1,2,4 \
  --steps 40 \
  --min-quorum-ratio 0.5 \
  --trainer numpy_convex \
  --payload-storage-mode chunked \
  --global-update-storage-mode chunked \
  --checkpoint-storage-mode chunked \
  --merge-mode streaming_chunked \
  --fragment-artifact-codec binary_v1 \
  --tensor-artifact-codec binary_v1 \
  --checkpoint-artifact-codec binary_v1 \
  --out /tmp/decodilo-m014a-learner-local/report.json
```

These commands are planning and local calibration only. They do not call cloud
APIs, allocate GPUs, or enable a remote artifact backend.

## Remote backend design validation

```bash
python -m decodilo.cli remote requirements \
  --scaling-report /tmp/decodilo-pod-optimization.json \
  --out /tmp/decodilo-remote-requirements.json
```

```bash
python -m decodilo.cli remote simulate-backend \
  --requirements /tmp/decodilo-remote-requirements.json \
  --read-gbps 10 \
  --write-gbps 5 \
  --ops-per-second 1000 \
  --strong-consistency \
  --conditional-put \
  --object-versioning \
  --seed 123 \
  --out /tmp/decodilo-remote-sim.json
```

```bash
python -m decodilo.cli remote validate-design \
  --requirements /tmp/decodilo-remote-requirements.json \
  --sim-report /tmp/decodilo-remote-sim.json \
  --out /tmp/decodilo-remote-design-validation.json
```

```bash
python -m decodilo.cli remote security-check \
  --requirements /tmp/decodilo-remote-requirements.json \
  --out /tmp/decodilo-remote-security.json
```

```bash
python -m decodilo.cli remote cost-estimate \
  --requirements /tmp/decodilo-remote-requirements.json \
  --cost-profile-json /tmp/manual-cost-profile.json \
  --out /tmp/decodilo-remote-cost.json
```

These are evidence and simulation commands only. They do not call cloud APIs,
read credentials, create remote objects, or enable a remote artifact backend.

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

Run Milestone 014 CI-safe lifecycle and binary perf soaks:

```bash
python -m decodilo.cli local soak \
  --profile lifecycle_ci \
  --workdir /tmp/decodilo-m014-lifecycle-ci

python -m decodilo.cli local soak \
  --profile binary_perf_ci \
  --workdir /tmp/decodilo-m014-binary-perf-ci
```

Long soak profiles require `--long`:

```bash
python -m decodilo.cli local soak \
  --profile local_long_lifecycle \
  --workdir /tmp/decodilo-m014-long \
  --long
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

Run the canonical local test profiles:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -o cache_dir=/tmp/decodilo-pytest-cache-full
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" -o cache_dir=/tmp/decodilo-pytest-cache-quick
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "lambda_offline and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-lambda-offline
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "runtime_local and not lambda_live and not lambda_real_mutation" -o cache_dir=/tmp/decodilo-pytest-cache-runtime-local
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_torch_causal_lm_optional.py tests/test_torch_runtime_local_optional.py -q -o cache_dir=/tmp/decodilo-pytest-cache-torch
```

`quick` is an explicit representative marker profile, not the old broad
"everything not slow" command. Lambda live and real mutation tests are manual
operator profiles and do not run by default.
Subprocess recovery tests such as `test_local_recovery_after_kill` are
`runtime_local`/`subprocess_heavy` and intentionally excluded from quick.

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

Characterize local runtime overhead and run a small perf matrix:

```bash
python -m decodilo.cli perf characterize \
  --workdir /tmp/decodilo-m014-perf \
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
  --allow-spill-to-disk \
  --out /tmp/decodilo-m014-perf/perf_characterization.json

python -m decodilo.cli perf matrix \
  --workdir /tmp/decodilo-m014-perf-matrix \
  --trainer numpy_convex \
  --learners 1,2,4 \
  --elements 1024,8192 \
  --chunk-size-kb 64,256 \
  --steps 40 \
  --min-quorum 1 \
  --codec binary_v1 \
  --out /tmp/decodilo-m014-perf-matrix/matrix.json
```

Check an explicit overhead budget:

```bash
python -m decodilo.cli perf check-budget \
  --report /tmp/decodilo-m014-perf/perf_characterization.json \
  --budget-json /tmp/decodilo-m014-perf/overhead_budget.json
```

Probe local hardware without requiring torch or accelerators:

```bash
python -m decodilo.cli hardware probe
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

## Review Lambda capacity follow-up

M043 analyzes capacity rejections without launching or mutating Lambda
resources. It distinguishes a provider capacity rejection with no instance
created from a teardown incident, then ranks catalog-backed alternatives for a
future review.

```bash
python -m decodilo.cli lambda capacity history \
  --latest-closeout /tmp/decodilo-lambda-m042-capacity-error-closeout.json \
  --previous-closeout /tmp/decodilo-lambda-capacity-error-closeout.json \
  --out /tmp/decodilo-lambda-capacity-history.json
```

```bash
python -m decodilo.cli lambda catalog-rotation rank \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --capacity-history /tmp/decodilo-lambda-capacity-history.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --max-budget 50 \
  --out /tmp/decodilo-lambda-catalog-rotation-rank.json
```

All M043 artifacts remain review-only and must report `launch_ready=false` and
`launch_allowed=false`.

## Record Lambda catalog rotation operator decision

M044 records the explicit operator decision for the M043-selected
`gpu_8x_a100_80gb_sxm4` catalog-rotation candidate. It does not launch,
terminate, mutate Lambda resources, or spend money.

Accepted-candidate path:

```bash
python -m decodilo.cli lambda catalog-rotation cost-review \
  --rotation-rank /tmp/decodilo-lambda-catalog-rotation-rank.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --out /tmp/decodilo-lambda-catalog-rotation-cost-review.json

python -m decodilo.cli lambda catalog-rotation risk-acceptance-template \
  --accept-selected-candidate \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-catalog-rotation-risk-acceptance.json

python -m decodilo.cli lambda catalog-rotation operator-decision \
  --risk-acceptance /tmp/decodilo-lambda-catalog-rotation-risk-acceptance.json \
  --out /tmp/decodilo-lambda-catalog-rotation-operator-decision.json

python -m decodilo.cli lambda catalog-rotation authorize-m045 \
  --capacity-history /tmp/decodilo-lambda-capacity-history.json \
  --retry-policy /tmp/decodilo-lambda-capacity-retry-policy.json \
  --rotation-rank /tmp/decodilo-lambda-catalog-rotation-rank.json \
  --cost-review /tmp/decodilo-lambda-catalog-rotation-cost-review.json \
  --risk-acceptance /tmp/decodilo-lambda-catalog-rotation-risk-acceptance.json \
  --operator-decision /tmp/decodilo-lambda-catalog-rotation-operator-decision.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-m045-catalog-rotation-authorization.json
```

Declined wait/manual paths use the same cost review, then either
`--decline-wait` or `--decline-manual-selection` in the risk-acceptance command.
Accepted risk may authorize only a future M045 review; command previews remain
non-executable and all M044 artifacts keep `launch_ready=false` and
`launch_allowed=false`.

## Regenerate flexible selector launch review

M044G supersedes fixed-shape future launch review with selector-driven review.
The selected shape must come from flexible selector output, not hardcoded
M039/M045 artifacts. M044G does not launch, terminate, mutate Lambda resources,
or spend money.

```bash
python -m decodilo.cli lambda availability-first select \
  --discovery-report /tmp/decodilo-lambda-m044g-readonly-discovery.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --max-budget 50 \
  --catalog-only-risk-accepted \
  --out /tmp/decodilo-lambda-flex-selector-risk-accepted.json

python -m decodilo.cli lambda flexible-selector operator-approval-template \
  --approve-future-review \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-flex-selector-operator-approval.json

python -m decodilo.cli lambda flexible-selector authorize \
  --selector-output /tmp/decodilo-lambda-flex-selector-risk-accepted.json \
  --operator-approval /tmp/decodilo-lambda-flex-selector-operator-approval.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --out /tmp/decodilo-lambda-flex-selector-authorization.json

python -m decodilo.cli lambda flexible-selector gate-check \
  --authorization /tmp/decodilo-lambda-flex-selector-authorization.json \
  --selector-output /tmp/decodilo-lambda-flex-selector-risk-accepted.json \
  --out /tmp/decodilo-lambda-flex-selector-gate-check.json

python -m decodilo.cli lambda flexible-selector fixed-shape-audit \
  --authorization /tmp/decodilo-lambda-flex-selector-authorization.json \
  --out /tmp/decodilo-lambda-flex-selector-fixed-shape-audit.json

python -m decodilo.cli lambda flexible-selector command-preview \
  --authorization /tmp/decodilo-lambda-flex-selector-authorization.json \
  --gate-check /tmp/decodilo-lambda-flex-selector-gate-check.json \
  --fixed-shape-audit /tmp/decodilo-lambda-flex-selector-fixed-shape-audit.json \
  --out /tmp/decodilo-lambda-flex-selector-command-preview.json
```

Flexible selector command previews remain non-executable and must not include
raw SSH key names.

## Make flexible selector capacity-history-aware

M044H prevents the flexible selector from selecting a shape that recently
returned provider capacity errors unless fresh live availability evidence or a
separate same-shape retry acceptance exists. Generic catalog-only risk
acceptance does not override capacity history. M044H is review-only and does
not launch, terminate, mutate Lambda resources, or spend money.

```bash
python -m decodilo.cli lambda flexible-selector capacity-aware-select \
  --capacity-history /tmp/decodilo-lambda-capacity-history.json \
  --capacity-retry-policy /tmp/decodilo-lambda-capacity-retry-policy.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --max-budget 50 \
  --out /tmp/decodilo-lambda-capacity-aware-flex-selector.json

python -m decodilo.cli lambda flexible-selector capacity-aware-authorize \
  --selector-output /tmp/decodilo-lambda-capacity-aware-flex-selector.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-capacity-aware-flex-authorization.json

python -m decodilo.cli lambda flexible-selector capacity-aware-gate-check \
  --authorization /tmp/decodilo-lambda-capacity-aware-flex-authorization.json \
  --selector-output /tmp/decodilo-lambda-capacity-aware-flex-selector.json \
  --out /tmp/decodilo-lambda-capacity-aware-flex-gate-check.json
```

The same-shape retry acceptance command exists only for an explicit future
same-shape retry review:

```bash
python -m decodilo.cli lambda flexible-selector same-shape-retry-acceptance \
  --shape gpu_1x_h100_pcie \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-same-shape-capacity-retry-acceptance.json
```

## Approve capacity-history-selected candidate for future M046 review

M045 records the explicit operator decision for the candidate selected by the
capacity-history-aware selector. Approval is future-only: it can produce an M046
review package and a non-executable command preview, but it must not launch,
terminate, mutate Lambda resources, or spend money.

```bash
python -m decodilo.cli lambda capacity-selected cost-risk-review \
  --selector-output /tmp/decodilo-lambda-capacity-aware-flex-selector.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --capacity-history /tmp/decodilo-lambda-capacity-history.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-capacity-selected-cost-risk-review.json

python -m decodilo.cli lambda capacity-selected operator-approval-template \
  --approve-future-m046 \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-capacity-selected-operator-approval.json

python -m decodilo.cli lambda capacity-selected authorize-m046 \
  --cost-risk-review /tmp/decodilo-lambda-capacity-selected-cost-risk-review.json \
  --operator-approval /tmp/decodilo-lambda-capacity-selected-operator-approval.json \
  --selector-authorization /tmp/decodilo-lambda-capacity-aware-flex-authorization.json \
  --selector-gate-check /tmp/decodilo-lambda-capacity-aware-flex-gate-check.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-m046-authorization.json
```

M046 real execution must use the explicit capacity-selected artifact flags. If
any M046 flag is supplied, `lambda m029 run` requires the full M046 artifact set
and blocks old M028/M029 and M039 lower-cost fallback paths. The execution gate
and preview remain offline until a separate supervised launch milestone:

```bash
python -m decodilo.cli lambda capacity-selected execution-gate-check \
  --m046-authorization /tmp/decodilo-lambda-m046-authorization.json \
  --cost-risk-review /tmp/decodilo-lambda-capacity-selected-cost-risk-review.json \
  --operator-approval /tmp/decodilo-lambda-capacity-selected-operator-approval.json \
  --capacity-selected-gate-check /tmp/decodilo-lambda-capacity-selected-gate-check.json \
  --capacity-aware-selector-output /tmp/decodilo-lambda-capacity-aware-flex-selector.json \
  --capacity-aware-selector-authorization /tmp/decodilo-lambda-capacity-aware-flex-authorization.json \
  --capacity-aware-selector-gate-check /tmp/decodilo-lambda-capacity-aware-flex-gate-check.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-capacity-selected-execution-gate-check.json

python -m decodilo.cli lambda m046a report \
  --execution-gate-check /tmp/decodilo-lambda-capacity-selected-execution-gate-check.json \
  --command-preview /tmp/decodilo-lambda-m046-command-preview.json \
  --out /tmp/decodilo-lambda-m046a-report.json
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
- Local performance characterization reports, perf matrix runs, overhead budget
  checks, guarded long soak profiles, resumable GC trash cleanup, reachability
  graph reports, and optional single-device hardware probes.

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
See `docs/performance_characterization.md`, `docs/overhead_budget.md`,
`docs/long_soak_profiles.md`, `docs/gc_cleanup.md`, and
`docs/optional_hardware_probe.md` for Milestone 014.
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

python -m decodilo.cli artifacts trash inspect \
  --workdir /tmp/decodilo-run

python -m decodilo.cli artifacts trash cleanup \
  --workdir /tmp/decodilo-run \
  --dry-run \
  --out /tmp/decodilo-run/trash_cleanup_report.json

python -m decodilo.cli artifacts reachability \
  --workdir /tmp/decodilo-run \
  --out /tmp/decodilo-run/reachability_graph.json
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

Quick CI uses the explicit M048 quick marker profile:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -m "quick and not slow and not soak and not perf and not integration and not lifecycle and not hardware_optional and not lambda_live and not lambda_real_mutation and not subprocess_heavy and not launch_history_heavy" -o cache_dir=/tmp/decodilo-pytest-cache-quick
```

Cloud launch remains disabled. No Lambda API, credential, GPU, CUDA, or remote
artifact backend exists in this scaffold.

## Milestone 016

Milestone 016 adds the readiness gate and provider-neutral conformance evidence
required before future remote backend SDK work can be reviewed. It is still
local-only: no SDKs, no credentials, no real remote backend, and no cloud launch.

```bash
python -m decodilo.cli remote conformance run \
  --requirements /tmp/decodilo-remote-requirements.json \
  --simulator-config /tmp/simulator-config.json \
  --out /tmp/remote-conformance.json

python -m decodilo.cli remote readiness evaluate \
  --requirements /tmp/decodilo-remote-requirements.json \
  --validation-report /tmp/decodilo-remote-design-validation.json \
  --conformance-report /tmp/remote-conformance.json \
  --security-report /tmp/decodilo-remote-security.json \
  --out /tmp/remote-readiness.json

python -m decodilo.cli remote evidence build \
  --workdir /tmp/decodilo-remote-evidence \
  --scaling-report /tmp/scaling.json \
  --requirements /tmp/requirements.json \
  --validation-report /tmp/validation.json \
  --conformance-report /tmp/conformance.json \
  --security-report /tmp/security.json \
  --cost-report /tmp/cost.json \
  --readiness-report /tmp/readiness.json \
  --out /tmp/evidence-package.json

python -m decodilo.cli remote provider-matrix \
  --requirements /tmp/requirements.json \
  --providers-json /tmp/manual-providers.json \
  --out /tmp/provider-matrix.json
```

Simulator conformance does not permit SDK addition and does not enable remote
backend execution. `remote_backend_enabled=false`, `launch_ready=false`, and
`launch_allowed=false` remain enforced.

## Milestone 017

Milestone 017 creates a review-only workflow for a future remote backend
implementation proposal. It consumes M016 evidence and produces proposal,
SDK-guard, risk, rollout, decision, and review-package artifacts. It still adds
no SDK, credentials, real backend, or cloud launch path.

```bash
python -m decodilo.cli remote proposal build \
  --requirements /tmp/requirements.json \
  --evidence-package /tmp/evidence-package.json \
  --provider-matrix /tmp/provider-matrix.json \
  --provider-name manual-simulated \
  --out /tmp/remote-proposal.json

python -m decodilo.cli remote sdk-guard \
  --project-root . \
  --out /tmp/sdk-guard.json

python -m decodilo.cli remote risk-register \
  --proposal /tmp/remote-proposal.json \
  --out /tmp/risk-register.json

python -m decodilo.cli remote rollout-plan \
  --proposal /tmp/remote-proposal.json \
  --out /tmp/rollout-plan.json

python -m decodilo.cli remote decision-record \
  --proposal /tmp/remote-proposal.json \
  --evidence-package /tmp/evidence-package.json \
  --readiness-report /tmp/readiness.json \
  --risk-register /tmp/risk-register.json \
  --sdk-guard-report /tmp/sdk-guard.json \
  --out /tmp/decision-record.json

python -m decodilo.cli remote review-package \
  --proposal /tmp/remote-proposal.json \
  --decision-record /tmp/decision-record.json \
  --risk-register /tmp/risk-register.json \
  --rollout-plan /tmp/rollout-plan.json \
  --sdk-guard-report /tmp/sdk-guard.json \
  --out /tmp/review-package.json
```

`candidate_for_future_sdk_review` is still review-only. It does not permit SDK
addition and does not enable remote backend execution.

## Milestone 018

Milestone 018 defines the Lambda Cloud API boundary using fixtures and a local
fake transport only. It adds typed Lambda fixture models, a disabled client, a
read-only fake client, a mutation guard, symbolic credential refs, a resource
ledger, dry-run Lambda launch/teardown plans, Lambda preflight, and flake-audit
tooling. It still performs no real Lambda API calls, reads no API keys, launches
nothing, terminates nothing, and cannot mutate remote resources.

```bash
python -m decodilo.cli lambda fake-discover \
  --fixtures-dir tests/fixtures/lambda_cloud \
  --out /tmp/lambda-discovery.json

python -m decodilo.cli lambda mutation-guard \
  --operation list_instances

python -m decodilo.cli lambda mutation-guard \
  --operation launch_instance

python -m decodilo.cli lambda plan \
  --discovery-report /tmp/lambda-discovery.json \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --nodes 1 \
  --region us-west-1 \
  --hours 1 \
  --max-run-budget 100 \
  --out /tmp/lambda-launch-plan.json

python -m decodilo.cli lambda ledger reconcile \
  --discovery-report /tmp/lambda-discovery.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --out /tmp/lambda-ledger.json

python -m decodilo.cli lambda preflight \
  --launch-plan /tmp/lambda-launch-plan.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --ledger /tmp/lambda-ledger.json \
  --out /tmp/lambda-preflight.json
```

Every Lambda report keeps `live_api_used=false`, `launch_ready=false`, and
`launch_allowed=false`. Mutation and unknown operations are denied by default.

## Milestone 019

Milestone 019 adds opt-in live Lambda Cloud read-only discovery. A real Lambda
API key may be used only from an explicit local file and only for read/list/get
discovery. Decodilo still cannot launch, terminate, restart, create, delete,
SSH, run setup scripts, or train on Lambda.

```bash
python -m decodilo.cli lambda live-discover \
  --api-key-file /path/to/lambda_api_key.txt \
  --live-read-only \
  --out /tmp/lambda-live-discovery.json

python -m decodilo.cli lambda audit-read-only \
  --discovery-report /tmp/lambda-live-discovery.json \
  --out /tmp/lambda-read-only-audit.json

python -m decodilo.cli lambda live-ledger reconcile \
  --discovery-report /tmp/lambda-live-discovery.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --out /tmp/lambda-live-ledger.json

python -m decodilo.cli lambda live-preflight \
  --discovery-report /tmp/lambda-live-discovery.json \
  --read-only-audit /tmp/lambda-read-only-audit.json \
  --ledger /tmp/lambda-live-ledger.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --out /tmp/lambda-live-preflight.json
```

Reports keep `billable_action_performed=false`, `launch_ready=false`, and
`launch_allowed=false`. Default tests use fake/local transports only and never
call the real Lambda API.

## Milestone 019A

Milestone 019A/M019C calibrates real Lambda read-only discovery when an
operator provides a local key file or explicitly passes `.env` as the secret
source. It records endpoint coverage, response-shape drift, pagination/limit
evidence, redacted summaries, unmanaged-resource ledger state, optional
unsupported endpoint classification, and read-only preflight status. It still
cannot launch, terminate, restart, create, delete, SSH, run setup scripts,
train, or spend.

```bash
python -m decodilo.cli lambda live-discover \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --live-read-only \
  --endpoint-set standard \
  --max-pages 10 \
  --max-items 1000 \
  --out /tmp/decodilo-lambda-live-discovery.json \
  --summary-out /tmp/decodilo-lambda-live-summary.json \
  --redaction-mode local_private_report

python -m decodilo.cli lambda audit-read-only \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --out /tmp/decodilo-lambda-read-only-audit.json

python -m decodilo.cli lambda live-ledger reconcile \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --out /tmp/decodilo-lambda-live-ledger.json

python -m decodilo.cli lambda live-preflight \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --read-only-audit /tmp/decodilo-lambda-read-only-audit.json \
  --ledger /tmp/decodilo-lambda-live-ledger.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --out /tmp/decodilo-lambda-live-preflight.json
```

Use `--redaction-mode public_summary` for shareable summaries. Default tests
remain fake/fixture-only and do not require internet or a Lambda API key.
The `.env` source is never auto-loaded, must be explicitly passed, and should be
ignored or untracked by git. Quota/usage 404s are recorded as optional
unsupported endpoints rather than parser failures.

## Milestone 020

Milestone 020 reconciles read-only Lambda discovery evidence with local price
snapshots, dry-run plans, live ledgers, teardown plans, and human approval
manifests. It is still not a launch milestone and adds no mutation-capable
client behavior.

```bash
python -m decodilo.cli lambda m020-reconcile \
  --discovery-report /tmp/decodilo-lambda-live-discovery.json \
  --read-only-audit /tmp/decodilo-lambda-read-only-audit.json \
  --ledger /tmp/decodilo-lambda-live-ledger.json \
  --launch-plan /tmp/lambda-launch-plan.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --credits 7500 \
  --max-run-budget 50 \
  --planned-hours 0.5 \
  --safety-buffer-percentage 15 \
  --out /tmp/decodilo-lambda-m020-readiness.json

python -m decodilo.cli lambda approval-template \
  --instance-type gpu_8x_h100_sxm \
  --region us-west-1 \
  --gpu-type "H100 SXM" \
  --gpus-per-instance 8 \
  --max-budget 50 \
  --max-runtime-minutes 30 \
  --out /tmp/lambda-approval-template.json

python -m decodilo.cli lambda readiness-summary \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json
```

M020 can identify a future fake launch lifecycle candidate, but
`future_real_launch_candidate=false`, `launch_ready=false`, and
`launch_allowed=false` remain enforced. It does not launch, terminate, restart,
create, delete, SSH, train, mutate, or spend.

## Milestone 021

Milestone 021 rehearses the Lambda launch/teardown lifecycle using local fake
state transitions and synthetic resource IDs only. It proves journaling,
idempotency, failure recovery, orphan detection, and termination verification
without calling Lambda or mutating any real resource.

```bash
python -m decodilo.cli lambda fake-lifecycle preflight \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --out /tmp/lambda-fake-lifecycle-preflight.json

python -m decodilo.cli lambda fake-lifecycle run \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --workdir /tmp/decodilo-lambda-fake-lifecycle \
  --idempotency-key fake-launch-001 \
  --out /tmp/decodilo-lambda-fake-lifecycle/report.json

python -m decodilo.cli lambda fake-lifecycle teardown \
  --lifecycle-report /tmp/decodilo-lambda-fake-lifecycle/report.json \
  --out /tmp/decodilo-lambda-fake-lifecycle/teardown-report.json

python -m decodilo.cli lambda fake-lifecycle verify \
  --lifecycle-report /tmp/decodilo-lambda-fake-lifecycle/report.json \
  --teardown-report /tmp/decodilo-lambda-fake-lifecycle/teardown-report.json \
  --out /tmp/decodilo-lambda-fake-lifecycle/verify.json

python -m decodilo.cli lambda fake-lifecycle fault \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --failure-mode fail_after_launch_before_health \
  --workdir /tmp/decodilo-lambda-fake-fault \
  --out /tmp/decodilo-lambda-fake-fault/report.json
```

`lambda approval-template --approve-fake-lifecycle` can produce only
`approved_for_future_fake_launch_lifecycle`; it cannot approve real launch.
M021 still performs no real launch, no real terminate, no restart, no create or
delete, no SSH, no setup scripts, no Lambda mutation, and no spend.

## Milestone 022

Milestone 022 adds a fake mutation-shaped Lambda API harness and fake lifecycle
stress evidence. The fake API models launch, terminate, restart, SSH-key, and
filesystem response shapes locally with synthetic IDs only. It does not add real
Lambda mutation behavior.

```bash
python -m decodilo.cli lambda fake-mutation contract \
  --lifecycle-report /tmp/decodilo-lambda-fake-lifecycle/teardown-report.json \
  --out /tmp/decodilo-lambda-fake-lifecycle/mutation-contract.json

python -m decodilo.cli lambda fake-lifecycle stress \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --workdir /tmp/decodilo-lambda-fake-stress \
  --cycles 5 \
  --failure-modes none,duplicate_launch_request,fail_after_launch_before_health,partial_terminate_failure \
  --out /tmp/decodilo-lambda-fake-stress/stress-report.json

python -m decodilo.cli lambda fake-lifecycle teardown-audit \
  --lifecycle-report /tmp/decodilo-lambda-fake-lifecycle/report.json \
  --teardown-report /tmp/decodilo-lambda-fake-lifecycle/teardown-report.json \
  --out /tmp/decodilo-lambda-fake-lifecycle/teardown-audit.json

python -m decodilo.cli lambda real-mutation-absence-audit \
  --project-root . \
  --out /tmp/decodilo-real-mutation-absence-audit.json

python -m decodilo.cli lambda fake-lifecycle evidence-package \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --preflight-report /tmp/lambda-fake-lifecycle-preflight.json \
  --stress-report /tmp/decodilo-lambda-fake-stress/stress-report.json \
  --teardown-audit /tmp/decodilo-lambda-fake-lifecycle/teardown-audit.json \
  --out /tmp/decodilo-lambda-fake-launch-readiness-package.json
```

M022 remains fake/local/audit only: no real launch, no real terminate, no
restart, no create/delete, no SSH, no setup scripts, no real Lambda mutation,
and no spend. `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false` remain enforced.

## Milestone 023

Milestone 023 creates a review-only real Lambda mutation boundary proposal and
first-launch safety case. It does not add real mutation transport, launch,
terminate, restart, create, or delete execution.

```bash
python -m decodilo.cli lambda real-mutation proposal \
  --m019c-discovery /tmp/decodilo-lambda-live-discovery-m19c.json \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --m022-readiness-package /tmp/decodilo-lambda-fake-launch-readiness-package.json \
  --real-mutation-absence-audit /tmp/decodilo-real-mutation-absence-audit.json \
  --out /tmp/decodilo-lambda-real-mutation-proposal.json

python -m decodilo.cli lambda real-mutation operation-spec \
  --out /tmp/decodilo-lambda-real-mutation-operation-spec.json

python -m decodilo.cli lambda real-mutation arming-gate \
  --out /tmp/decodilo-lambda-real-mutation-arming-gate.json

python -m decodilo.cli lambda real-mutation safety-case \
  --proposal /tmp/decodilo-lambda-real-mutation-proposal.json \
  --operation-spec /tmp/decodilo-lambda-real-mutation-operation-spec.json \
  --fake-lifecycle-evidence /tmp/decodilo-lambda-fake-launch-readiness-package.json \
  --out /tmp/decodilo-lambda-first-launch-safety-case.json

python -m decodilo.cli lambda real-mutation evidence-package \
  --m019c-discovery /tmp/decodilo-lambda-live-discovery-m19c.json \
  --m019c-audit /tmp/decodilo-lambda-read-only-audit-m19c.json \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --m022-readiness-package /tmp/decodilo-lambda-fake-launch-readiness-package.json \
  --proposal /tmp/decodilo-lambda-real-mutation-proposal.json \
  --operation-spec /tmp/decodilo-lambda-real-mutation-operation-spec.json \
  --safety-case /tmp/decodilo-lambda-first-launch-safety-case.json \
  --out /tmp/decodilo-lambda-first-launch-evidence-package.json

python -m decodilo.cli lambda real-mutation review-record \
  --evidence-package /tmp/decodilo-lambda-first-launch-evidence-package.json \
  --out /tmp/decodilo-lambda-real-mutation-review-record.json
```

M023 can produce `design_review_ready` for a human review record when evidence
is complete, but it still keeps `real_mutation_enabled=false`,
`launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`. There is still no real mutation, no launch,
no terminate, and no spend.

## Milestone 024

Milestone 024 adds a disabled real-mutation transport skeleton and executable
path proof. It defines the future code boundary for mutation operations while
proving that launch and terminate methods raise before request construction.

```bash
python -m decodilo.cli lambda real-mutation skeleton-audit \
  --project-root . \
  --out /tmp/decodilo-lambda-real-mutation-skeleton-audit.json

python -m decodilo.cli lambda real-mutation budget-lock \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --approval-manifest /tmp/lambda-approval-fake-lifecycle.json \
  --out /tmp/decodilo-lambda-budget-lock.json

python -m decodilo.cli lambda real-mutation idempotency-plan \
  --run-id run-example \
  --operation launch_one_instance \
  --plan-hash example-plan-hash \
  --out /tmp/decodilo-lambda-idempotency-plan.json

python -m decodilo.cli lambda real-mutation resource-scope \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --out /tmp/decodilo-lambda-resource-scope.json

python -m decodilo.cli lambda real-mutation prepare-launch \
  --proposal /tmp/decodilo-lambda-real-mutation-proposal.json \
  --operation-spec /tmp/decodilo-lambda-real-mutation-operation-spec.json \
  --budget-lock /tmp/decodilo-lambda-budget-lock.json \
  --idempotency-plan /tmp/decodilo-lambda-idempotency-plan.json \
  --resource-scope /tmp/decodilo-lambda-resource-scope.json \
  --out /tmp/decodilo-lambda-prepare-launch.json

python -m decodilo.cli lambda real-mutation disabled-launch-test \
  --prepare-launch /tmp/decodilo-lambda-prepare-launch.json \
  --out /tmp/decodilo-lambda-disabled-launch-test.json
```

M024 remains skeleton/audit only. The request builder emits review-only plans
without executable URLs, methods, or bodies. Feature flags and arming state
cannot enable mutation. `real_mutation_enabled=false`, `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false` remain enforced.

## Milestone 025

Milestone 025 creates the final prelaunch review gate for a future first
one-instance Lambda launch. It produces evidence packages, non-executable
runbooks, an operator checklist, semantic no-mutation audit, and a go/no-go
design record. It still does not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda final-prelaunch evidence-package \
  --m019c-discovery /tmp/decodilo-lambda-live-discovery-m19c.json \
  --m019c-audit /tmp/decodilo-lambda-read-only-audit-m19c.json \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --m022-readiness-package /tmp/decodilo-lambda-fake-launch-readiness-package.json \
  --m023-evidence-package /tmp/decodilo-lambda-first-launch-evidence-package.json \
  --m024-skeleton-audit /tmp/decodilo-lambda-real-mutation-skeleton-audit.json \
  --out /tmp/decodilo-lambda-final-prelaunch-evidence.json

python -m decodilo.cli lambda final-prelaunch runbook \
  --out /tmp/decodilo-lambda-first-launch-runbook.json

python -m decodilo.cli lambda final-prelaunch termination-runbook \
  --out /tmp/decodilo-lambda-termination-runbook.json

python -m decodilo.cli lambda final-prelaunch checklist-template \
  --out /tmp/decodilo-lambda-operator-checklist.json

python -m decodilo.cli lambda final-prelaunch semantic-audit \
  --project-root . \
  --out /tmp/decodilo-lambda-semantic-mutation-audit.json

python -m decodilo.cli lambda final-prelaunch review \
  --evidence-package /tmp/decodilo-lambda-final-prelaunch-evidence.json \
  --operator-checklist /tmp/decodilo-lambda-operator-checklist.json \
  --semantic-audit /tmp/decodilo-lambda-semantic-mutation-audit.json \
  --out /tmp/decodilo-lambda-final-prelaunch-review.json

python -m decodilo.cli lambda final-prelaunch go-no-go \
  --review /tmp/decodilo-lambda-final-prelaunch-review.json \
  --out /tmp/decodilo-lambda-go-no-go.json
```

The highest positive M025 status is
`go_for_future_m026_real_launch_review`. This is not launch approval.
`real_mutation_enabled=false`, `launch_ready=false`, `launch_allowed=false`,
and `billable_action_performed=false` remain enforced.

## Milestone 026

Milestone 026 adds the human-reviewed decision gate for whether M027 may
implement minimal real Lambda mutation code disabled by default. It still does
not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda decision human-review-template \
  --m025-evidence-package /tmp/decodilo-lambda-final-prelaunch-evidence.json \
  --go-no-go /tmp/decodilo-lambda-go-no-go.json \
  --out /tmp/decodilo-lambda-human-review.json

python -m decodilo.cli lambda decision validate-human-review \
  --human-review /tmp/decodilo-lambda-human-review.json \
  --out /tmp/decodilo-lambda-human-review-validation.json

python -m decodilo.cli lambda decision freshness \
  --m019c-discovery /tmp/decodilo-lambda-live-discovery-m19c.json \
  --price-snapshot /tmp/lambda-price-snapshot.json \
  --m025-review /tmp/decodilo-lambda-final-prelaunch-review.json \
  --out /tmp/decodilo-lambda-evidence-freshness.json

python -m decodilo.cli lambda decision blocker-matrix \
  --human-review-validation /tmp/decodilo-lambda-human-review-validation.json \
  --freshness-report /tmp/decodilo-lambda-evidence-freshness.json \
  --semantic-audit /tmp/decodilo-lambda-semantic-mutation-audit.json \
  --out /tmp/decodilo-lambda-blocker-matrix.json

python -m decodilo.cli lambda decision decide \
  --human-review-validation /tmp/decodilo-lambda-human-review-validation.json \
  --freshness-report /tmp/decodilo-lambda-evidence-freshness.json \
  --blocker-matrix /tmp/decodilo-lambda-blocker-matrix.json \
  --m025-review /tmp/decodilo-lambda-final-prelaunch-review.json \
  --out /tmp/decodilo-lambda-m026-decision.json

python -m decodilo.cli lambda decision m027-authorization \
  --decision-record /tmp/decodilo-lambda-m026-decision.json \
  --out /tmp/decodilo-lambda-m027-authorization.json

python -m decodilo.cli lambda decision report \
  --decision-record /tmp/decodilo-lambda-m026-decision.json \
  --authorization-record /tmp/decodilo-lambda-m027-authorization.json \
  --out /tmp/decodilo-lambda-m026-report.json
```

Allowed M026 decisions are `blocked`, `needs_more_evidence`, and
`approve_m027_minimal_real_mutation_implementation`. The positive decision is
implementation authorization only. It is not launch approval; no real Lambda
mutation path is executable.

## Milestone 027

Milestone 027 adds the minimal Lambda mutation-shaped request path for local
fake-server execution only. It can prepare and execute fake
`launch_one_instance` and `terminate_owned_instance` flows against an in-memory
or localhost fake server, but it rejects real Lambda URLs, credentials, and any
attempt to enable real execution.

```bash
python -m decodilo.cli lambda minimal-mutation fake-run \
  --m027-authorization /tmp/decodilo-lambda-m027-authorization.json \
  --operation-spec /tmp/decodilo-lambda-real-mutation-operation-spec.json \
  --budget-lock /tmp/decodilo-lambda-budget-lock.json \
  --idempotency-plan /tmp/decodilo-lambda-idempotency-plan.json \
  --resource-scope /tmp/decodilo-lambda-resource-scope.json \
  --teardown-plan /tmp/lambda-teardown-plan.json \
  --workdir /tmp/decodilo-lambda-minimal-fake-run \
  --out /tmp/decodilo-lambda-minimal-fake-run/report.json

python -m decodilo.cli lambda minimal-mutation preflight \
  --m027-authorization /tmp/decodilo-lambda-m027-authorization.json \
  --operation-spec /tmp/decodilo-lambda-real-mutation-operation-spec.json \
  --budget-lock /tmp/decodilo-lambda-budget-lock.json \
  --idempotency-plan /tmp/decodilo-lambda-idempotency-plan.json \
  --resource-scope /tmp/decodilo-lambda-resource-scope.json \
  --out /tmp/decodilo-lambda-minimal-mutation-preflight.json

python -m decodilo.cli lambda minimal-mutation audit \
  --fake-run-report /tmp/decodilo-lambda-minimal-fake-run/report.json \
  --out /tmp/decodilo-lambda-minimal-mutation-audit.json

python -m decodilo.cli lambda minimal-mutation blocked-real-url-test \
  --out /tmp/decodilo-lambda-blocked-real-url-test.json
```

M027 remains fake-server execution only: no real Lambda launch, no real
termination, no credentials, no SSH, no setup scripts, no training, and no
spend. `real_mutation_enabled=false`, `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false` remain enforced.

## Milestone 028

Milestone 028 creates the final authorization package for a future M029 first
real one-instance Lambda launch attempt. It does not launch, terminate, mutate,
or spend. The only positive decision is
`authorized_for_m029_one_instance_launch_attempt`, and it remains next-milestone
authorization only.

```bash
python -m decodilo.cli lambda m028 fresh-readonly-refresh \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --out /tmp/decodilo-lambda-m028-readonly-refresh.json

python -m decodilo.cli lambda m028 state-snapshot \
  --discovery-report /tmp/decodilo-lambda-live-discovery-m19c.json \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --out /tmp/decodilo-lambda-m028-state-snapshot.json

python -m decodilo.cli lambda m028 budget-lock \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --out /tmp/decodilo-lambda-m028-budget-lock.json

python -m decodilo.cli lambda m028 resource-lock \
  --m020-report /tmp/decodilo-lambda-m020-readiness.json \
  --out /tmp/decodilo-lambda-m028-resource-lock.json

python -m decodilo.cli lambda m028 launch-window-lock \
  --max-runtime-minutes 30 \
  --out /tmp/decodilo-lambda-m028-launch-window-lock.json

python -m decodilo.cli lambda m028 teardown-plan \
  --out /tmp/decodilo-lambda-m028-teardown-verification-plan.json

python -m decodilo.cli lambda m028 operator-confirmation-template \
  --out /tmp/decodilo-lambda-m028-operator-confirmation.json

python -m decodilo.cli lambda m028 final-no-mutation-audit \
  --project-root . \
  --out /tmp/decodilo-lambda-m028-no-mutation-audit.json

python -m decodilo.cli lambda m028 authorize-m029 \
  --state-snapshot /tmp/decodilo-lambda-m028-state-snapshot.json \
  --budget-lock /tmp/decodilo-lambda-m028-budget-lock.json \
  --resource-lock /tmp/decodilo-lambda-m028-resource-lock.json \
  --launch-window-lock /tmp/decodilo-lambda-m028-launch-window-lock.json \
  --teardown-plan /tmp/decodilo-lambda-m028-teardown-verification-plan.json \
  --operator-confirmation /tmp/decodilo-lambda-m028-operator-confirmation.json \
  --no-mutation-audit /tmp/decodilo-lambda-m028-no-mutation-audit.json \
  --out /tmp/decodilo-lambda-m029-authorization.json

python -m decodilo.cli lambda m028 decision \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --out /tmp/decodilo-lambda-m028-decision.json

python -m decodilo.cli lambda m028 report \
  --decision /tmp/decodilo-lambda-m028-decision.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --out /tmp/decodilo-lambda-m028-report.json
```

M028 warning: no real launch, no real terminate, no mutation, no spend, no SSH,
no setup scripts, and no training. `real_mutation_enabled=false`,
`launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false` remain enforced.

## Milestone 029

M029 is the first billable milestone. It may attempt exactly one real Lambda
launch only after every gate passes, then it must terminate that exact owned
instance and verify termination through Lambda read-only get/list. Restart,
create/delete, SSH, setup scripts, cloud-init, training, background execution,
and unowned termination remain forbidden.

```bash
python -m decodilo.cli lambda m029 run \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --m028-report /tmp/decodilo-lambda-m028-report.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --workdir /tmp/decodilo-lambda-m029 \
  --execute-real-launch \
  --confirm-billable-action "I understand this may create a billable Lambda instance and must be terminated" \
  --confirm-terminate-required "I understand this run must terminate the owned instance and verify termination"
```

Fake-server test form:

```bash
python -m decodilo.cli lambda m029 run \
  --m028-report /tmp/decodilo-lambda-m028-report.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --workdir /tmp/decodilo-lambda-m029-fake \
  --in-memory-fake \
  --execute-real-launch \
  --confirm-billable-action "I understand this may create a billable Lambda instance and must be terminated" \
  --confirm-terminate-required "I understand this run must terminate the owned instance and verify termination"
```

Post-run helpers:

```bash
python -m decodilo.cli lambda m029 verify --workdir /tmp/decodilo-lambda-m029
python -m decodilo.cli lambda m029 spend-audit --workdir /tmp/decodilo-lambda-m029
```

Operator presence is required for the entire launch window. The hard scope is
one instance, 30 minutes, and $50. If a launch request is sent or may have
succeeded, termination verification is mandatory.
### Milestone 029B

M029B repairs the first-launch evidence path without launching anything. It imports
operator-provided Lambda product catalog or manual price snapshots, builds shape
evidence, classifies live availability as inconclusive when instance-type discovery
returns an empty list, and resolves the planned launch shape from catalog plus
non-sample price evidence.

Example commands:

```bash
python -m decodilo.cli lambda price import-catalog \
  --input /path/to/lambda_instances_snapshot.html \
  --source-url https://lambda.ai/instances \
  --out /tmp/decodilo-lambda-price-snapshot-real-catalog.json

python -m decodilo.cli lambda shape-evidence build-catalog \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --out /tmp/decodilo-lambda-shape-evidence.json

python -m decodilo.cli lambda shape-evidence availability \
  --discovery-report /tmp/decodilo-lambda-m029a-live-discovery.json \
  --out /tmp/decodilo-lambda-availability-evidence.json

python -m decodilo.cli lambda shape-evidence resolve \
  --planned-shape /tmp/decodilo-lambda-m020-readiness.json \
  --catalog-evidence /tmp/decodilo-lambda-shape-evidence.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --availability-evidence /tmp/decodilo-lambda-availability-evidence.json \
  --out /tmp/decodilo-lambda-shape-resolution.json
```

M029B remains non-launching: no real launch, no terminate, no mutation, no spend.

### Milestone 029D

M029D records the ambiguous M029C first-launch outcome and blocks any second
launch attempt until incident closeout is complete. It performs no launch and no
automatic termination.

Incident closeout commands:

```bash
python -m decodilo.cli lambda m029 incident console-confirmation \
  --lambda-console-checked \
  --no-instances-visible \
  --no-pending-instances-visible \
  --no-alert-instances-visible \
  --out /tmp/decodilo-lambda-m029c-console-confirmation.json

python -m decodilo.cli lambda m029 incident discovery-diff \
  --pre-discovery /tmp/decodilo-lambda-m029c-readonly-refresh.json \
  --post-discovery /tmp/decodilo-lambda-post-m029c-discovery.json \
  --ledger /tmp/decodilo-lambda-m029c/ledger.json \
  --out /tmp/decodilo-lambda-m029c-discovery-diff.json

python -m decodilo.cli lambda m029 incident report \
  --m029-report /tmp/decodilo-lambda-m029c/report.json \
  --discovery-diff /tmp/decodilo-lambda-m029c-discovery-diff.json \
  --console-confirmation /tmp/decodilo-lambda-m029c-console-confirmation.json \
  --out /tmp/decodilo-lambda-m029c-incident-report.json

python -m decodilo.cli lambda m029 incident second-attempt-check \
  --incident-report /tmp/decodilo-lambda-m029c-incident-report.json \
  --out /tmp/decodilo-lambda-m029c-second-attempt-check.json
```

No second launch is permitted while the M029C incident is open or unresolved.
M029D does not restart, create/delete resources, SSH, run setup scripts, train,
or authorize spend.

### Milestone 030

M030 reviews whether the closed M029C incident permits a future M031
second-attempt review. It does not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda second-attempt risk-review \
  --incident-report /tmp/decodilo-lambda-m029e-incident-report.json \
  --out /tmp/decodilo-lambda-second-risk-review.json

python -m decodilo.cli lambda second-attempt mitigation-review \
  --incident-report /tmp/decodilo-lambda-m029e-incident-report.json \
  --prior-m029-report /tmp/decodilo-lambda-m029c/report.json \
  --out /tmp/decodilo-lambda-second-mitigation-review.json

python -m decodilo.cli lambda second-attempt correlation-plan \
  --prior-m029-report /tmp/decodilo-lambda-m029c/report.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --out /tmp/decodilo-lambda-second-correlation-plan.json

python -m decodilo.cli lambda second-attempt reconciliation-plan \
  --out /tmp/decodilo-lambda-second-reconciliation-plan.json

python -m decodilo.cli lambda second-attempt authorize \
  --incident-report /tmp/decodilo-lambda-m029e-incident-report.json \
  --risk-review /tmp/decodilo-lambda-second-risk-review.json \
  --mitigation-review /tmp/decodilo-lambda-second-mitigation-review.json \
  --correlation-plan /tmp/decodilo-lambda-second-correlation-plan.json \
  --reconciliation-plan /tmp/decodilo-lambda-second-reconciliation-plan.json \
  --out /tmp/decodilo-lambda-second-authorization.json

python -m decodilo.cli lambda second-attempt go-no-go \
  --authorization /tmp/decodilo-lambda-second-authorization.json \
  --out /tmp/decodilo-lambda-second-go-no-go.json
```

The highest M030 positive status is
`go_for_future_m031_second_launch_review`. `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false` remain enforced.

### Milestone 031D

M031D closes out the M031 response-loss incident and adds a global future-launch
hold after two lost launch responses. It does not launch, terminate, mutate, or
spend beyond read-only discovery.

Incident closeout commands:

```bash
python -m decodilo.cli lambda m031 incident console-confirmation \
  --lambda-console-checked \
  --no-instances-visible \
  --no-pending-instances-visible \
  --no-alert-instances-visible \
  --no-owned-instance-found \
  --out /tmp/decodilo-lambda-m031d-console-confirmation.json

python -m decodilo.cli lambda m031 incident discovery-diff \
  --pre-discovery /tmp/decodilo-lambda-m031-readonly-refresh.json \
  --post-discovery /tmp/decodilo-lambda-post-m031-discovery.json \
  --closeout-discovery /tmp/decodilo-lambda-m031d-readonly-discovery.json \
  --ledger /tmp/decodilo-lambda-m031/ledger.json \
  --out /tmp/decodilo-lambda-m031d-discovery-diff.json

python -m decodilo.cli lambda m031 incident report \
  --m031-report /tmp/decodilo-lambda-m031/report.json \
  --discovery-diff /tmp/decodilo-lambda-m031d-discovery-diff.json \
  --console-confirmation /tmp/decodilo-lambda-m031d-console-confirmation.json \
  --out /tmp/decodilo-lambda-m031d-incident-report.json

python -m decodilo.cli lambda m031 incident repeated-response-loss-review \
  --m029c-report /tmp/decodilo-lambda-m029c/report.json \
  --m031-report /tmp/decodilo-lambda-m031/report.json \
  --m029e-closeout /tmp/decodilo-lambda-m029e-incident-closeout.json \
  --m031-closeout /tmp/decodilo-lambda-m031d-incident-closeout.json \
  --out /tmp/decodilo-lambda-repeated-response-loss-review.json

python -m decodilo.cli lambda m031 incident future-launch-hold \
  --m031-incident-report /tmp/decodilo-lambda-m031d-incident-report.json \
  --repeated-response-loss-review /tmp/decodilo-lambda-repeated-response-loss-review.json \
  --out /tmp/decodilo-lambda-future-launch-hold.json
```

Future launch remains blocked until the repeated response-loss mitigation is
accepted and fresh operator approval is obtained. `launch_ready=false` and
`launch_allowed=false` remain enforced.

### Milestone 032

M032 instruments the launch/terminate transport boundary without launching or
terminating anything. It captures HTTP status before parsing, redacts response
metadata, verifies endpoint specs offline, runs response-loss regression
fixtures, evaluates mitigation acceptance, and releases the future-launch hold
only for future review.

```bash
python -m decodilo.cli lambda response-loss endpoint-spec \
  --operation launch_one_instance \
  --method POST \
  --path-template /instance-operations/launch \
  --source-url https://docs.lambda.ai/public-cloud/cloud-api/ \
  --confidence medium \
  --out /tmp/decodilo-lambda-launch-endpoint-spec.json

python -m decodilo.cli lambda response-loss diagnostics-fixture \
  --scenario launch_status_200_empty_body \
  --out /tmp/decodilo-lambda-response-loss-diagnostic.json

python -m decodilo.cli lambda response-loss regression-harness \
  --out /tmp/decodilo-lambda-response-loss-regression.json

python -m decodilo.cli lambda response-loss mitigation-acceptance \
  --endpoint-spec /tmp/decodilo-lambda-launch-endpoint-spec.json \
  --regression-report /tmp/decodilo-lambda-response-loss-regression.json \
  --out /tmp/decodilo-lambda-response-loss-mitigation-acceptance.json

python -m decodilo.cli lambda response-loss hold-release \
  --m031-incident-report /tmp/decodilo-lambda-m031-incident-report.json \
  --mitigation-acceptance /tmp/decodilo-lambda-response-loss-mitigation-acceptance.json \
  --out /tmp/decodilo-lambda-future-launch-hold-release.json
```

M032 does not authorize launch. `launch_ready=false`, `launch_allowed=false`,
and `billable_action_performed=false` remain enforced.

### Milestone 033

M033 creates a third-attempt authorization review package for a future M034
one-instance launch attempt using M032 response-loss mitigation evidence. It
does not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda third-attempt endpoint-confirmation \
  --endpoint-spec /tmp/decodilo-lambda-launch-endpoint-spec.json \
  --accept-medium-confidence \
  --out /tmp/decodilo-lambda-third-endpoint-confirmation.json

python -m decodilo.cli lambda third-attempt response-capture-lock \
  --out /tmp/decodilo-lambda-response-capture-settings-lock.json

python -m decodilo.cli lambda third-attempt timeout-policy \
  --launch-timeout-seconds 30 \
  --terminate-timeout-seconds 30 \
  --read-only-verification-timeout-seconds 120 \
  --out /tmp/decodilo-lambda-launch-timeout-policy.json

python -m decodilo.cli lambda third-attempt risk-review \
  --m029c-report /tmp/decodilo-lambda-m029c/report.json \
  --m031-report /tmp/decodilo-lambda-m031/report.json \
  --m031d-closeout /tmp/decodilo-lambda-m031d-incident-closeout.json \
  --mitigation-acceptance /tmp/decodilo-lambda-response-loss-mitigation-acceptance.json \
  --endpoint-confirmation /tmp/decodilo-lambda-third-endpoint-confirmation.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --out /tmp/decodilo-lambda-third-risk-review.json

python -m decodilo.cli lambda third-attempt correlation-plan \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --response-capture-lock /tmp/decodilo-lambda-response-capture-settings-lock.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --out /tmp/decodilo-lambda-third-correlation-plan.json

python -m decodilo.cli lambda third-attempt reconciliation-plan \
  --out /tmp/decodilo-lambda-third-reconciliation-plan.json

python -m decodilo.cli lambda third-attempt authorize \
  --m031d-closeout /tmp/decodilo-lambda-m031d-incident-closeout.json \
  --mitigation-acceptance /tmp/decodilo-lambda-response-loss-mitigation-acceptance.json \
  --hold-release /tmp/decodilo-lambda-future-launch-hold-release.json \
  --endpoint-confirmation /tmp/decodilo-lambda-third-endpoint-confirmation.json \
  --response-capture-lock /tmp/decodilo-lambda-response-capture-settings-lock.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --risk-review /tmp/decodilo-lambda-third-risk-review.json \
  --correlation-plan /tmp/decodilo-lambda-third-correlation-plan.json \
  --reconciliation-plan /tmp/decodilo-lambda-third-reconciliation-plan.json \
  --renewed-operator-approval \
  --out /tmp/decodilo-lambda-m034-authorization.json

python -m decodilo.cli lambda third-attempt go-no-go \
  --authorization /tmp/decodilo-lambda-m034-authorization.json \
  --out /tmp/decodilo-lambda-third-go-no-go.json

python -m decodilo.cli lambda third-attempt report \
  --endpoint-confirmation /tmp/decodilo-lambda-third-endpoint-confirmation.json \
  --response-capture-lock /tmp/decodilo-lambda-response-capture-settings-lock.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --risk-review /tmp/decodilo-lambda-third-risk-review.json \
  --correlation-plan /tmp/decodilo-lambda-third-correlation-plan.json \
  --reconciliation-plan /tmp/decodilo-lambda-third-reconciliation-plan.json \
  --authorization /tmp/decodilo-lambda-m034-authorization.json \
  --go-no-go /tmp/decodilo-lambda-third-go-no-go.json \
  --out /tmp/decodilo-lambda-m033-report.json
```

M033 can authorize only future M034 review, not execution. `launch_ready=false`,
`launch_allowed=false`, `real_mutation_enabled=false`, and
`billable_action_performed=false` remain enforced.

### Milestone 034A

M034A wires the M033 third-attempt mitigation artifacts into the M029 run path
without launching, terminating, mutating, or spending. The new M034 gate check
must pass before a future third launch attempt can construct a mutation request.

```bash
python -m decodilo.cli lambda m034 gate-check \
  --m028-report /tmp/decodilo-lambda-m028-report.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --endpoint-confirmation /tmp/decodilo-lambda-third-endpoint-confirmation.json \
  --response-capture-lock /tmp/decodilo-lambda-response-capture-settings-lock.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --risk-review /tmp/decodilo-lambda-third-risk-review.json \
  --correlation-plan /tmp/decodilo-lambda-third-correlation-plan.json \
  --reconciliation-plan /tmp/decodilo-lambda-third-reconciliation-plan.json \
  --m034-authorization /tmp/decodilo-lambda-m034-authorization.json \
  --third-go-no-go /tmp/decodilo-lambda-third-go-no-go.json \
  --m033-report /tmp/decodilo-lambda-m033-report.json \
  --out /tmp/decodilo-lambda-m034-gate-check.json
```

A future M034 run must pass the same artifact set explicitly:

```bash
python -m decodilo.cli lambda m029 run \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --m028-report /tmp/decodilo-lambda-m028-report.json \
  --m029-authorization /tmp/decodilo-lambda-m029-authorization.json \
  --endpoint-confirmation /tmp/decodilo-lambda-third-endpoint-confirmation.json \
  --response-capture-lock /tmp/decodilo-lambda-response-capture-settings-lock.json \
  --timeout-policy /tmp/decodilo-lambda-launch-timeout-policy.json \
  --risk-review /tmp/decodilo-lambda-third-risk-review.json \
  --correlation-plan /tmp/decodilo-lambda-third-correlation-plan.json \
  --reconciliation-plan /tmp/decodilo-lambda-third-reconciliation-plan.json \
  --m034-authorization /tmp/decodilo-lambda-m034-authorization.json \
  --third-go-no-go /tmp/decodilo-lambda-third-go-no-go.json \
  --m033-report /tmp/decodilo-lambda-m033-report.json \
  --workdir /tmp/decodilo-lambda-m034 \
  --execute-real-launch \
  --confirm-billable-action "I understand this may create a billable Lambda instance and must be terminated" \
  --confirm-terminate-required "I understand this run must terminate the owned instance and verify termination"
```

The M034 gate enforces a launch timeout of at least 30 seconds,
`no_auto_launch_retry=true`, response capture before parsing, endpoint
confirmation, the third-attempt correlation key, and the reconciliation policy.
Missing or invalid M033/M034 artifacts block before request construction.
M034A itself remains non-launching: `launch_ready=false`,
`launch_allowed=false`, `real_mutation_enabled=false`, and
`billable_action_performed=false`.

### Milestone 034D

M034D closes the M034C ambiguous launch incident and hardens transport failure
persistence. It does not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda m034 incident console-confirmation \
  --lambda-console-checked \
  --no-instances-visible \
  --no-pending-instances-visible \
  --no-alert-instances-visible \
  --no-owned-instance-found \
  --out /tmp/decodilo-lambda-m034c-console-confirmation.json

python -m decodilo.cli lambda m034 incident discovery-diff \
  --pre-discovery /tmp/decodilo-lambda-m034c-readonly-refresh.json \
  --post-discovery /tmp/decodilo-lambda-post-m034c-discovery-late.json \
  --ledger /tmp/decodilo-lambda-m034c/ledger.json \
  --out /tmp/decodilo-lambda-m034c-discovery-diff.json

python -m decodilo.cli lambda m034 incident recover-from-journal \
  --journal /tmp/decodilo-lambda-m034c/journal.jsonl \
  --report /tmp/decodilo-lambda-m034c/report.json \
  --out /tmp/decodilo-lambda-m034c-journal-recovery.json

python -m decodilo.cli lambda m034 incident report \
  --journal /tmp/decodilo-lambda-m034c/journal.jsonl \
  --discovery-diff /tmp/decodilo-lambda-m034c-discovery-diff.json \
  --console-confirmation /tmp/decodilo-lambda-m034c-console-confirmation.json \
  --out /tmp/decodilo-lambda-m034c-incident-report.json

python -m decodilo.cli lambda m034 incident closeout \
  --incident-report /tmp/decodilo-lambda-m034c-incident-report.json \
  --out /tmp/decodilo-lambda-m034c-closeout.json

python -m decodilo.cli lambda m034 diagnostics validate-crash-safe \
  --failure-report /tmp/decodilo-lambda-m034c/mutation-failure-report.json \
  --diagnostic-report /tmp/decodilo-lambda-m034c/transport-diagnostics.json \
  --out /tmp/decodilo-lambda-m034c-crash-safe-diagnostics.json

python -m decodilo.cli lambda m034 incident future-launch-hold \
  --incident-report /tmp/decodilo-lambda-m034c-incident-report.json \
  --crash-safe-diagnostics /tmp/decodilo-lambda-m034c-crash-safe-diagnostics.json \
  --out /tmp/decodilo-lambda-m034c-future-launch-hold.json
```

Any active M034 future-launch hold blocks `lambda m029 run` before request
construction when passed via `--m034-future-launch-hold`. Clearing the hold is
for future review only; it does not authorize launch.

### Milestone 035

M035 creates a post-incident launch strategy decision after the M029C, M031, and
M034C ambiguous launch outcomes. It does not launch, terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda post-incident attempt-history \
  --m029-report /tmp/decodilo-lambda-m029c/report.json \
  --m031-report /tmp/decodilo-lambda-m031/report.json \
  --m034-recovery /tmp/decodilo-lambda-m034e-incident-report.json \
  --out /tmp/decodilo-lambda-launch-attempt-history.json

python -m decodilo.cli lambda post-incident endpoint-confidence \
  --endpoint-spec /tmp/decodilo-lambda-launch-endpoint-spec.json \
  --attempt-history /tmp/decodilo-lambda-launch-attempt-history.json \
  --out /tmp/decodilo-lambda-endpoint-confidence-review.json

python -m decodilo.cli lambda post-incident shape-strategy \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --current-shape gpu_8x_h100_sxm \
  --out /tmp/decodilo-lambda-shape-strategy-review.json

python -m decodilo.cli lambda post-incident option-matrix \
  --attempt-history /tmp/decodilo-lambda-launch-attempt-history.json \
  --endpoint-confidence /tmp/decodilo-lambda-endpoint-confidence-review.json \
  --shape-strategy /tmp/decodilo-lambda-shape-strategy-review.json \
  --out /tmp/decodilo-lambda-fourth-option-matrix.json

python -m decodilo.cli lambda post-incident support-request \
  --out /tmp/decodilo-lambda-support-evidence-request.json

python -m decodilo.cli lambda post-incident decide \
  --option-matrix /tmp/decodilo-lambda-fourth-option-matrix.json \
  --out /tmp/decodilo-lambda-m035-decision.json

python -m decodilo.cli lambda post-incident report \
  --attempt-history /tmp/decodilo-lambda-launch-attempt-history.json \
  --endpoint-confidence /tmp/decodilo-lambda-endpoint-confidence-review.json \
  --shape-strategy /tmp/decodilo-lambda-shape-strategy-review.json \
  --option-matrix /tmp/decodilo-lambda-fourth-option-matrix.json \
  --support-request /tmp/decodilo-lambda-support-evidence-request.json \
  --decision /tmp/decodilo-lambda-m035-decision.json \
  --out /tmp/decodilo-lambda-m035-report.json
```

After three response-loss outcomes, medium endpoint confidence should trigger
support/operator confirmation before another real launch unless a future
operator explicitly accepts that risk. Lower-cost shape reauthorization is also
considered for lifecycle-only smoke testing. M035 can authorize only a future
milestone path; it keeps `launch_ready=false`, `launch_allowed=false`,
`real_mutation_enabled=false`, and `billable_action_performed=false`.

### Milestone 036

M036 requests and validates Lambda support/operator endpoint evidence and
reviews lower-cost lifecycle smoke shapes. It does not launch, terminate,
mutate, or spend.

```bash
python -m decodilo.cli lambda support-confirmation request \
  --out /tmp/decodilo-lambda-support-confirmation-request.json

python -m decodilo.cli lambda support-confirmation ingest \
  --input /tmp/operator-support-response.json \
  --out /tmp/decodilo-lambda-support-confirmation-response.json

python -m decodilo.cli lambda support-confirmation validate \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --out /tmp/decodilo-lambda-support-confirmation-validation.json

python -m decodilo.cli lambda support-confirmation endpoint-behavior \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --out /tmp/decodilo-lambda-endpoint-behavior-evidence.json

python -m decodilo.cli lambda support-confirmation response-shape \
  --endpoint-behavior /tmp/decodilo-lambda-endpoint-behavior-evidence.json \
  --out /tmp/decodilo-lambda-response-shape-evidence.json

python -m decodilo.cli lambda support-confirmation idempotency-semantics \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --out /tmp/decodilo-lambda-idempotency-semantics.json

python -m decodilo.cli lambda support-confirmation ambiguous-semantics \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --out /tmp/decodilo-lambda-ambiguous-response-semantics.json

python -m decodilo.cli lambda support-confirmation endpoint-confidence-upgrade \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --endpoint-behavior /tmp/decodilo-lambda-endpoint-behavior-evidence.json \
  --response-shape /tmp/decodilo-lambda-response-shape-evidence.json \
  --idempotency-semantics /tmp/decodilo-lambda-idempotency-semantics.json \
  --ambiguous-response-semantics /tmp/decodilo-lambda-ambiguous-response-semantics.json \
  --out /tmp/decodilo-lambda-endpoint-confidence-upgrade.json

python -m decodilo.cli lambda lower-cost-shape review \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --current-shape gpu_8x_h100_sxm \
  --out /tmp/decodilo-lambda-lower-cost-shape-review.json

python -m decodilo.cli lambda m036 strategy-decision \
  --endpoint-confidence-upgrade /tmp/decodilo-lambda-endpoint-confidence-upgrade.json \
  --lower-cost-shape-review /tmp/decodilo-lambda-lower-cost-shape-review.json \
  --out /tmp/decodilo-lambda-m036-strategy-decision.json

python -m decodilo.cli lambda m036 report \
  --support-request /tmp/decodilo-lambda-support-confirmation-request.json \
  --support-response /tmp/decodilo-lambda-support-confirmation-response.json \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --endpoint-confidence-upgrade /tmp/decodilo-lambda-endpoint-confidence-upgrade.json \
  --lower-cost-shape-review /tmp/decodilo-lambda-lower-cost-shape-review.json \
  --strategy-decision /tmp/decodilo-lambda-m036-strategy-decision.json \
  --out /tmp/decodilo-lambda-m036-report.json
```

If no real support/operator response exists yet, M036 can still emit the support
request, lower-cost shape review, and an M036 report whose decision is
`require_more_support_evidence`. Support evidence must not contain API keys,
Authorization headers, or bearer tokens.

### Milestone 037

M037 ingests a real support/operator response if present and decides whether
endpoint confidence can upgrade and whether `gpu_1x_h100_pcie` should be
reauthorized for a future lifecycle-only launch smoke test. It does not launch,
terminate, mutate, or spend.

```bash
python -m decodilo.cli lambda support-confirmation ingest \
  --input /tmp/operator-support-response.json \
  --out /tmp/decodilo-lambda-support-confirmation-response.json

python -m decodilo.cli lambda support-confirmation validate \
  --response /tmp/decodilo-lambda-support-confirmation-response.json \
  --out /tmp/decodilo-lambda-support-confirmation-validation.json

python -m decodilo.cli lambda support-confirmation evidence-package \
  --support-request /tmp/decodilo-lambda-support-confirmation-request.json \
  --support-response /tmp/decodilo-lambda-support-confirmation-response.json \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --endpoint-confidence-upgrade /tmp/decodilo-lambda-endpoint-confidence-upgrade.json \
  --out /tmp/decodilo-lambda-support-response-evidence-package.json

python -m decodilo.cli lambda support-confirmation endpoint-decision \
  --validation /tmp/decodilo-lambda-support-confirmation-validation.json \
  --endpoint-confidence-upgrade /tmp/decodilo-lambda-endpoint-confidence-upgrade.json \
  --out /tmp/decodilo-lambda-endpoint-confidence-decision.json

python -m decodilo.cli lambda lower-cost-shape operator-selection \
  --lower-cost-review /tmp/decodilo-lambda-lower-cost-shape-review.json \
  --support-response /tmp/decodilo-lambda-support-confirmation-response.json \
  --out /tmp/decodilo-lambda-lower-cost-shape-selection.json

python -m decodilo.cli lambda lower-cost-shape reauthorization-package \
  --selection /tmp/decodilo-lambda-lower-cost-shape-selection.json \
  --out /tmp/decodilo-lambda-lower-cost-reauthorization-package.json

python -m decodilo.cli lambda m037 decide \
  --support-evidence-package /tmp/decodilo-lambda-support-response-evidence-package.json \
  --endpoint-decision /tmp/decodilo-lambda-endpoint-confidence-decision.json \
  --shape-selection /tmp/decodilo-lambda-lower-cost-shape-selection.json \
  --reauthorization-package /tmp/decodilo-lambda-lower-cost-reauthorization-package.json \
  --out /tmp/decodilo-lambda-m037-decision.json

python -m decodilo.cli lambda m037 report \
  --decision /tmp/decodilo-lambda-m037-decision.json \
  --out /tmp/decodilo-lambda-m037-report.json
```

If `/tmp/operator-support-response.json` is absent, M037 must not fabricate one.
It records `require_more_support_evidence`, leaves endpoint confidence
unupgraded, and keeps `launch_ready=false` and `launch_allowed=false`.

### Milestone 036R

M036R supersedes the M036 support-confirmation path with an offline
compatibility audit against the known-working Strand-AI `lambda-cli`
implementation. The Strand CLI is unofficial and not affiliated with or
endorsed by Lambda; it is recorded only as operator-tested behavioral evidence.
M036R does not launch, terminate, mutate Lambda resources, or spend.

```bash
python -m decodilo.cli lambda strand-cli compatibility \
  --out /tmp/decodilo-lambda-strand-compatibility.json

python -m decodilo.cli lambda strand-cli gap-analysis \
  --out /tmp/decodilo-lambda-strand-gap-analysis.json

python -m decodilo.cli lambda strand-cli migration-plan \
  --gap-analysis /tmp/decodilo-lambda-strand-gap-analysis.json \
  --out /tmp/decodilo-lambda-strand-migration-plan.json

python -m decodilo.cli lambda strand-cli fixture-smoke \
  --out /tmp/decodilo-lambda-strand-fixture-smoke.json

python -m decodilo.cli lambda strand-cli m036r-report \
  --gap-analysis /tmp/decodilo-lambda-strand-gap-analysis.json \
  --out /tmp/decodilo-lambda-m036r-report.json
```

The compatibility target uses `POST /instance-operations/launch`,
`POST /instance-operations/terminate`, `data.instance_ids` launch responses,
2xx status-only termination success, an existing SSH key name, `quantity=1`,
and a 30 second timeout. All M036R reports keep `launch_ready=false`,
`launch_allowed=false`, and `billable_action_performed=false`.

### Milestone 037R

M037R builds a future-review, lower-cost Strand-compatible launch package for
`gpu_1x_h100_pcie`. It does not launch, terminate, mutate Lambda resources, or
spend. Strand compatibility requires an existing SSH key name, selected only
from read-only discovery or an operator-selected existing key.

```bash
python -m decodilo.cli lambda strand ssh-key-selection \
  --discovery-report /tmp/decodilo-lambda-m037r-readonly-discovery.json \
  --out /tmp/decodilo-lambda-strand-ssh-key-selection.json

python -m decodilo.cli lambda strand lower-cost-plan \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --region us-west-1 \
  --out /tmp/decodilo-lambda-strand-lower-cost-plan.json

python -m decodilo.cli lambda lower-cost price-reconcile \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --shape gpu_1x_h100_pcie \
  --out /tmp/decodilo-lambda-lower-cost-price-reconciliation.json

python -m decodilo.cli lambda lower-cost resource-reconcile \
  --discovery-report /tmp/decodilo-lambda-m037r-readonly-discovery.json \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-lower-cost-resource-reconciliation.json

python -m decodilo.cli lambda strand response-loss-controls \
  --out /tmp/decodilo-lambda-strand-response-loss-controls.json

python -m decodilo.cli lambda lower-cost authorization-package \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --price-reconciliation /tmp/decodilo-lambda-lower-cost-price-reconciliation.json \
  --resource-reconciliation /tmp/decodilo-lambda-lower-cost-resource-reconciliation.json \
  --strand-compatibility /tmp/decodilo-lambda-strand-compatibility.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-authorization-package.json

python -m decodilo.cli lambda lower-cost decision \
  --authorization-package /tmp/decodilo-lambda-lower-cost-authorization-package.json \
  --out /tmp/decodilo-lambda-lower-cost-future-launch-decision.json

python -m decodilo.cli lambda m037r report \
  --decision /tmp/decodilo-lambda-lower-cost-future-launch-decision.json \
  --out /tmp/decodilo-lambda-m037r-report.json
```

If no existing SSH key is available, M037R records the blocker and keeps
`launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.

### Milestone 038

M038 converts the M037R lower-cost review into a future M039 authorization
package. It does not launch, terminate, mutate Lambda resources, or spend. If
only the operator approval template exists, M039 authorization remains blocked
until explicit future approval is recorded.

```bash
python -m decodilo.cli lambda lower-cost canonical-readiness \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --price-reconciliation /tmp/decodilo-lambda-lower-cost-price-reconciliation.json \
  --resource-reconciliation /tmp/decodilo-lambda-lower-cost-resource-reconciliation.json \
  --out /tmp/decodilo-lambda-lower-cost-canonical-readiness.json

python -m decodilo.cli lambda lower-cost state-snapshot \
  --discovery-report /tmp/decodilo-lambda-m038-readonly-discovery.json \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --out /tmp/decodilo-lambda-lower-cost-state-snapshot.json

python -m decodilo.cli lambda lower-cost budget-lock \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --out /tmp/decodilo-lambda-lower-cost-budget-lock.json

python -m decodilo.cli lambda lower-cost resource-lock \
  --state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-lower-cost-resource-lock.json

python -m decodilo.cli lambda lower-cost launch-window-lock \
  --max-runtime-minutes 30 \
  --out /tmp/decodilo-lambda-lower-cost-launch-window-lock.json

python -m decodilo.cli lambda lower-cost operator-approval-template \
  --out /tmp/decodilo-lambda-lower-cost-operator-approval.json

python -m decodilo.cli lambda lower-cost authorize-m039 \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --operator-approval /tmp/decodilo-lambda-lower-cost-operator-approval.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-m039-authorization.json

python -m decodilo.cli lambda lower-cost gate-check \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-gate-check.json

python -m decodilo.cli lambda lower-cost command-preview \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --out /tmp/decodilo-lambda-m039-command-preview.json

python -m decodilo.cli lambda m038 report \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --gate-check /tmp/decodilo-lambda-lower-cost-gate-check.json \
  --command-preview /tmp/decodilo-lambda-m039-command-preview.json \
  --out /tmp/decodilo-lambda-m038-report.json
```

M038A records explicit lower-cost operator approval for a future M039 review.
It still does not launch, terminate, mutate Lambda resources, or enable
`launch_ready`/`launch_allowed`.

```bash
python -m decodilo.cli lambda lower-cost operator-approval-template \
  --approve-future-m039 \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-lower-cost-operator-approval.json

python -m decodilo.cli lambda lower-cost authorize-m039 \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --operator-approval /tmp/decodilo-lambda-lower-cost-operator-approval.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-m039-authorization.json

python -m decodilo.cli lambda lower-cost gate-check \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-gate-check.json

python -m decodilo.cli lambda lower-cost command-preview \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --out /tmp/decodilo-lambda-m039-command-preview.json

python -m decodilo.cli lambda m038a report \
  --authorization /tmp/decodilo-lambda-m039-authorization.json \
  --gate-check /tmp/decodilo-lambda-lower-cost-gate-check.json \
  --command-preview /tmp/decodilo-lambda-m039-command-preview.json \
  --operator-approval /tmp/decodilo-lambda-lower-cost-operator-approval.json \
  --out /tmp/decodilo-lambda-m038a-report.json
```

M039A wires the lower-cost execution path into `lambda m029 run` without
launching. If any lower-cost M039 flag is present, all lower-cost artifacts are
required and the old M028/M029 `gpu_8x_h100_sxm` resource path is not used.
The execution gate is offline and review-only:

```bash
python -m decodilo.cli lambda lower-cost execution-gate-check \
  --m039-authorization /tmp/decodilo-lambda-m039-authorization.json \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-execution-gate-check.json
```

Future M039 lower-cost execution must use the explicit lower-cost run flags:

```bash
python -m decodilo.cli lambda m029 run \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --m039-authorization /tmp/decodilo-lambda-m039-authorization.json \
  --lower-cost-canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --lower-cost-state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --lower-cost-budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --lower-cost-resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --lower-cost-launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --lower-cost-launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --lower-cost-gate-check /tmp/decodilo-lambda-lower-cost-gate-check.json \
  --m038a-report /tmp/decodilo-lambda-m038a-report.json \
  --workdir /tmp/decodilo-lambda-m039 \
  --execute-real-launch \
  --confirm-billable-action "I understand this may create a billable Lambda instance and must be terminated" \
  --confirm-terminate-required "I understand this run must terminate the owned instance and verify termination"
```

The raw existing SSH key name is consumed only from the private local SSH
selection artifact for request construction. Public reports, command previews,
and diagnostics keep only hash/redacted SSH key values. M039A fake-server tests
prove the lower-cost path launches and terminates one synthetic owned instance
without real Lambda API calls.

## Lambda M040 Capacity Closeout and Availability-First Review

M040 closes a lower-cost launch rejection when Lambda returns a structured 400
capacity error, no owned instance ID is recorded, and final read-only discovery
shows zero visible/unmanaged instances. It does not launch, terminate, or mutate
Lambda resources.

Review commands:

```bash
python -m decodilo.cli lambda capacity-error closeout \
  --m039-workdir /tmp/decodilo-lambda-m039c-error-message \
  --post-discovery /tmp/decodilo-lambda-post-m039c-error-message-discovery.json \
  --out /tmp/decodilo-lambda-capacity-error-closeout.json

python -m decodilo.cli lambda capacity-error policy \
  --capacity-closeout /tmp/decodilo-lambda-capacity-error-closeout.json \
  --out /tmp/decodilo-lambda-capacity-error-policy.json

python -m decodilo.cli lambda availability-first extract-candidates \
  --discovery-report /tmp/decodilo-lambda-post-m039c-error-message-discovery.json \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --out /tmp/decodilo-lambda-availability-candidates.json

python -m decodilo.cli lambda availability-first rank \
  --candidates /tmp/decodilo-lambda-availability-candidates.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --max-budget 50 \
  --out /tmp/decodilo-lambda-availability-rank.json

python -m decodilo.cli lambda availability-first plan \
  --rank /tmp/decodilo-lambda-availability-rank.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-availability-first-plan.json

python -m decodilo.cli lambda availability-first authorize \
  --capacity-closeout /tmp/decodilo-lambda-capacity-error-closeout.json \
  --capacity-policy /tmp/decodilo-lambda-capacity-error-policy.json \
  --rank /tmp/decodilo-lambda-availability-rank.json \
  --plan /tmp/decodilo-lambda-availability-first-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-availability-first-authorization.json

python -m decodilo.cli lambda availability-first go-no-go \
  --authorization /tmp/decodilo-lambda-availability-first-authorization.json \
  --out /tmp/decodilo-lambda-availability-first-go-no-go.json

python -m decodilo.cli lambda m040 report \
  --capacity-closeout /tmp/decodilo-lambda-capacity-error-closeout.json \
  --availability-authorization /tmp/decodilo-lambda-availability-first-authorization.json \
  --go-no-go /tmp/decodilo-lambda-availability-first-go-no-go.json \
  --out /tmp/decodilo-lambda-m040-report.json
```

The availability-first selector must not preselect one GPU shape. It ranks all
approved, priced, Strand-compatible quantity-1 candidates by live availability,
then buffered 30-minute cost, then single-GPU preference, then no-filesystem
requirement. If no live-available candidate exists, a catalog-only candidate may
be reported, but `launch_selection_allowed=false` unless the operator has
explicitly accepted catalog-only availability risk.

If live instance-type discovery returns no candidates, M040 records
`endpoint_inconclusive`. Catalog-only candidates can be ranked but require
future operator risk acceptance. Same fixed-shape retry stays blocked unless
fresh availability evidence changes.

## Lambda M041 Catalog Availability Risk Decision

M041 records the operator decision for catalog-only availability risk. It does
not launch, terminate, mutate resources, or spend money.

Accepted-risk path:

```bash
python -m decodilo.cli lambda catalog-availability risk-acceptance-template \
  --accept-risk \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json

python -m decodilo.cli lambda catalog-availability operator-decision \
  --risk-acceptance /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json \
  --out /tmp/decodilo-lambda-catalog-availability-operator-decision.json

python -m decodilo.cli lambda catalog-availability authorize-m042 \
  --capacity-closeout /tmp/decodilo-lambda-capacity-error-closeout.json \
  --availability-authorization /tmp/decodilo-lambda-availability-first-authorization.json \
  --go-no-go /tmp/decodilo-lambda-availability-first-go-no-go.json \
  --risk-acceptance /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json \
  --operator-decision /tmp/decodilo-lambda-catalog-availability-operator-decision.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-m042-authorization.json

python -m decodilo.cli lambda catalog-availability gate-check \
  --m042-authorization /tmp/decodilo-lambda-m042-authorization.json \
  --availability-plan /tmp/decodilo-lambda-availability-first-plan.json \
  --risk-acceptance /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --out /tmp/decodilo-lambda-catalog-availability-gate-check.json

python -m decodilo.cli lambda catalog-availability command-preview \
  --m042-authorization /tmp/decodilo-lambda-m042-authorization.json \
  --gate-check /tmp/decodilo-lambda-catalog-availability-gate-check.json \
  --out /tmp/decodilo-lambda-m042-command-preview.json

python -m decodilo.cli lambda m041 report \
  --risk-acceptance /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json \
  --operator-decision /tmp/decodilo-lambda-catalog-availability-operator-decision.json \
  --m042-authorization /tmp/decodilo-lambda-m042-authorization.json \
  --gate-check /tmp/decodilo-lambda-catalog-availability-gate-check.json \
  --command-preview /tmp/decodilo-lambda-m042-command-preview.json \
  --out /tmp/decodilo-lambda-m041-report.json
```

Declined-risk path:

```bash
python -m decodilo.cli lambda catalog-availability risk-acceptance-template \
  --decline-risk \
  --out /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json

python -m decodilo.cli lambda catalog-availability operator-decision \
  --risk-acceptance /tmp/decodilo-lambda-catalog-availability-risk-acceptance.json \
  --out /tmp/decodilo-lambda-catalog-availability-operator-decision.json

python -m decodilo.cli lambda catalog-availability wait-plan \
  --operator-decision /tmp/decodilo-lambda-catalog-availability-operator-decision.json \
  --out /tmp/decodilo-lambda-wait-for-live-availability-plan.json
```

M041 accepted risk authorizes only a future M042 review. The command preview
remains non-executable and keeps `launch_ready=false`, `launch_allowed=false`.
### Lambda Lifecycle Smoke Closeout

M047 records the successful M046C Lambda lifecycle smoke and hardens future shape/region
selection. The closeout artifacts preserve the successful launch/owned-termination
evidence, reconcile the final account state, parse live `/instance-types`, select a live
region, resolve stale shape aliases, and join canonical live shapes to non-sample price
evidence. M047 does not authorize or perform any new Lambda mutation; all M047 launch and
mutation flags remain false.

### Lambda Remote Bootstrap Planning

M050 prepares a future M051 remote runtime bootstrap review without launching, using
credentials, SSH, running remote commands, installing packages, or training. The default
bootstrap mode is metadata-only with SSH declined, an empty command allowlist, package
installation denied, and training denied. The M051 runbook preview is non-executable and
keeps `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.

M051A adds an offline one-shot arming bridge for a future supervised M051B
metadata-only execution attempt. Standing review artifacts remain non-executable with
`launch_ready=false`, `launch_allowed=false`, and `launch_authorized_now=false`; the
reviewer bridge is the only artifact that may expose
`one_shot_request_send_permitted=true`, and it is hash-bound to the exact command and
reviewed artifacts.

M052 closes out a completed M051B metadata-only bootstrap without making any Lambda API
calls. It records the success, reconciles the final discovery evidence, preserves hashes
for the M051B report/journal/ledger/spend audit, attests that no SSH or remote command
occurred, compares the result with the M046C lifecycle smoke, and writes a planning-only
M053 decision:

```bash
python -m decodilo.cli lambda metadata-bootstrap success-record \
  --workdir /tmp/decodilo-lambda-m051 \
  --post-discovery /tmp/decodilo-lambda-post-m051-discovery.json \
  --out /tmp/decodilo-lambda-metadata-bootstrap-success-record.json

python -m decodilo.cli lambda metadata-bootstrap closeout \
  --success-record /tmp/decodilo-lambda-metadata-bootstrap-success-record.json \
  --reconciliation /tmp/decodilo-lambda-metadata-bootstrap-reconciliation.json \
  --evidence-package /tmp/decodilo-lambda-metadata-bootstrap-evidence-package.json \
  --out /tmp/decodilo-lambda-metadata-bootstrap-closeout.json

python -m decodilo.cli lambda m053 decide \
  --metadata-closeout /tmp/decodilo-lambda-metadata-bootstrap-closeout.json \
  --strategy-update /tmp/decodilo-lambda-remote-bootstrap-strategy-update.json \
  --out /tmp/decodilo-lambda-m053-next-step-decision.json
```

M052 artifacts keep `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`; historical M051B spend is recorded only as
historical evidence.

M053 plans a future SSH-connectivity-only review without launching, calling live
Lambda APIs, using credentials, SSH, opening instance network connections, running
remote commands, transferring files, forwarding ports, installing packages, or
training. It defines the scope, credential policy, client policy, evidence schema,
operator approval model, command/file-transfer/port-forwarding prohibitions, risk
review, M054 future authorization package, and non-executable runbook preview:

```bash
python -m decodilo.cli lambda ssh-connectivity scope \
  --out /tmp/decodilo-lambda-ssh-connectivity-scope.json

python -m decodilo.cli lambda ssh-connectivity operator-approval-template \
  --out /tmp/decodilo-lambda-ssh-connectivity-operator-approval.json

python -m decodilo.cli lambda ssh-connectivity authorize-m054 \
  --risk-review /tmp/decodilo-lambda-ssh-connectivity-risk-review.json \
  --out /tmp/decodilo-lambda-m054-ssh-connectivity-authorization.json
```

If explicit operator approval is absent, M054 remains `not_authorized`. If approval
is later provided, authorization is still future-review only and keeps
`launch_ready=false`, `launch_allowed=false`, and `billable_action_performed=false`.

M054A prepares a future M054B SSH-connectivity-only execution package without
launching, calling live Lambda, using credentials, SSH, running commands, transferring
files, forwarding ports, installing packages, or training. It builds an execution
plan, private-key reference policy, non-executed safe SSH command preview, static
validator, one-shot arming artifact, reviewer bridge, no-exec audit, and command
preview:

```bash
python -m decodilo.cli lambda ssh-connectivity execution-plan \
  --authorization /tmp/decodilo-lambda-m054-ssh-connectivity-authorization.json \
  --out /tmp/decodilo-lambda-ssh-connectivity-execution-plan.json

python -m decodilo.cli lambda ssh-connectivity safe-client-command \
  --private-key-policy /tmp/decodilo-lambda-ssh-private-key-policy.json \
  --out /tmp/decodilo-lambda-ssh-safe-client-command.json

python -m decodilo.cli lambda ssh-connectivity reviewer-bridge \
  --arming /tmp/decodilo-lambda-m054-ssh-one-shot-arming.json \
  --static-validation /tmp/decodilo-lambda-ssh-connectivity-static-validation.json \
  --safe-client-command /tmp/decodilo-lambda-ssh-safe-client-command.json \
  --out /tmp/decodilo-lambda-m054-ssh-reviewer-bridge.json

python -m decodilo.cli lambda m054a report \
  --execution-plan /tmp/decodilo-lambda-ssh-connectivity-execution-plan.json \
  --static-validation /tmp/decodilo-lambda-ssh-connectivity-static-validation.json \
  --reviewer-bridge /tmp/decodilo-lambda-m054-ssh-reviewer-bridge.json \
  --no-exec-audit /tmp/decodilo-lambda-ssh-connectivity-no-exec-audit.json \
  --command-preview /tmp/decodilo-lambda-m054-ssh-command-preview.json \
  --out /tmp/decodilo-lambda-m054a-report.json
```

M054A adds future M054B CLI flags to `lambda m029 run`, but they are guarded in
M054A and cannot fall back to older launch paths. The generated preview remains
non-executable.

M055 closes out M054B as lifecycle-successful but SSH-host-discovery-blocked and
adds provider metadata host discovery for future SSH-connectivity attempts. Host
discovery records sanitized metadata key paths, rejects private/non-global IPs by
default, supports explicit `LAMBDA_SSH_HOST_OVERRIDE`, and terminates the owned
instance without attempting SSH if no host is found. Remote commands, file transfer,
port forwarding, package installation, setup scripts, cloud-init, and training remain
forbidden.
