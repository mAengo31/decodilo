# Decoupled DiLoCo Production-Scale Progress Record — 2026-07-01

Generated: 2026-07-01T13:50:50.804667+00:00
Branch: `codex/lambda-gpu-diloco-progress`

## Purpose

This document records the current state of the repo, the production-scale blockers, the verified changes made in this slice, the Lambda storage availability check, and the GitHub backup plan.

## Current target

Build a production-ready Decoupled DiLoCo system on Lambda GPUs:

```text
AdamW local training → Nesterov outer sync → chunked artifacts → resilient Lambda GPU learners/syncer → durable object storage → managed operation layer → production scale
```

## Production-scale map

```text
Toy prototype ✅
Local DiLoCo runtime ✅
Local AdamW/Nesterov runtime ✅
Chunked artifact runtime ✅
Single Lambda GPU proof ✅
4-learner Lambda GPU proof ✅
Durable local object-store proof ✅
S3-compatible adapter/factory 🟡 verified with fake client
Real external object-store smoke ❌ blocked by provider/config
Lambda run using external object store ❌ blocked by external object store
8+ learner / larger model / long run ❌ pending
Full Pathway-like scheduler ❌ pending
```

## Fixes already made toward production scale

### 1. Real DiLoCo optimizer path

- Implemented/verified local DiLoCo mechanics using AdamW as the inner optimizer and Nesterov as the outer optimizer.
- Added honest optimizer metadata and state handling.
- Added numeric pseudo-gradient validation instead of overclaiming that a code path alone was a numeric check.

### 2. Tiny trainer and trainer registry

- Added `tiny_adamw` trainer for CPU-only synthetic training mechanics.
- Registered trainer cleanly.
- Metadata avoids claiming paper-scale or real-model training when only synthetic mechanics are exercised.

### 3. Local learner/syncer runtime hardening

- Verified local learner/syncer path with two learners and one syncer.
- Verified chunked runtime, replay validation, metric validation, and checkpoint/restart recovery.

### 4. Chunked artifact transport

- Added chunked payloads/checkpoints/global updates.
- Added streaming chunked merge and binary tensor/fragment/checkpoint artifact codecs.
- Prevented giant model/update payloads from being embedded directly in JSON control messages.

### 5. Lambda GPU execution proofs

- Proved real Lambda GPU DiLoCo-style run.
- Proved four-learner Lambda GPU direct-TCP topology with one syncer.
- Verified cleanup back to zero live instances in prior evidence.

### 6. Pathway-lite operation layer

- Added operation specs/backends/results.
- Local operation backend delegates to `LocalRunner`.
- Lambda backend remains dry-run/blocked unless explicitly allowed.
- This is not full Google Pathways; it is an early managed-experiment layer.

### 7. Durable object-store shape

- Added durable filesystem object-store backend with persistent index, reopen/read after restart, range reads, list refs, and idempotent puts.
- Wired runtime artifacts through durable local object-store mode.

### 8. S3-compatible boundary in this slice

- Added `src/decodilo/storage/s3_client_factory.py`.
- Added explicit client/client-factory injection only.
- Preserved no SDK dependency, no env reads, no implicit network calls.
- Added in-process runtime injection hooks in `SyncerService` and `LearnerWorker`.
- Added S3-compatible mirror validation for artifact manifests and chunks.
- Added CLI fail-closed guard: `local run`, `syncer serve`, and `learner run` reject `artifact-storage-backend=s3_compatible` because subprocesses cannot receive an injected Python client object.

## Lambda storage availability check

Live read-only Lambda API check performed on 2026-07-01:

```text
GET /instances     → count=0
GET /file-systems  → count=0
```

Interpretation:

- There are currently no live Lambda instances.
- There are currently no Lambda Cloud file systems available in this account/region response.
- I did not find an account-provided S3 bucket to use from the live API check.
- Lambda has file-system concepts, and Lambda docs mention an S3 Adapter for mounting file systems as S3-compatible buckets, but this account currently reports no file systems.

Blocker:

```text
No Lambda-owned S3-compatible bucket/filesystem is currently available to run the external object-store experiment.
```

Likely alternatives:

1. Create/provision a Lambda Cloud filesystem if desired and allowed.
2. Use an external S3-compatible provider such as Cloudflare R2, AWS S3, GCS S3 interoperability, Backblaze B2, or MinIO.
3. Continue local/durable object-store tests until a real object-store endpoint is available.

## Verification from this slice

```text
python3 -m py_compile ...                                      PASS
python3 -m ruff check ...                                      PASS
pytest S3/fail-closed/no-SDK/preflight tests                   17 passed
pytest storage/remote backend focused suite                    42 passed
pytest live chunked runtime/cross-instance/security tests      11 passed
pytest token/replay/trainer contract tests                     9 passed
pytest -m quick                                                56 passed
manual remote s3-preflight                                     blocked as expected: client_not_injected
```

Broad non-live profile update after P1 hardening:

```text
2269 passed, 45 deselected
```

The previously failing Lambda fake lifecycle/gating tests, stale price-fixture tests, async learner inflight tests, local recovery flake, and durable replay mismatch were fixed in the follow-up hardening commit.

## Remaining blockers and priority

### P0 — Back up current verified work

- Commit this Markdown record plus S3/runtime changes.
- Push branch to GitHub.

### P1 — Resolve or quarantine broad-suite failures

Status: completed after follow-up hardening.

- Fixed stale Lambda price-fixture timestamps by generating fresh test timestamps.
- Fixed async learner inflight tests to await `_handle_global_payload`.
- Hardened local recovery test with enough post-restart runtime for the restarted learner to contribute.
- Fixed remote-command evidence field handling for optional `downloads_attempted` and related safety booleans.
- Fixed FragmentStore commit atomicity so failed chunked artifact writing cannot advance `global_version` or leave orphan `sync_round_started` events.

### P2 — Real external object-store smoke

Required before another production-shaped Lambda training run:

```text
put/get/range/list/delete/checksum/cleanup
```

### P3 — Lambda GPU DiLoCo with external object store

Run once a real object-store endpoint exists:

```text
4 learners + 1 syncer + GPU trainer + AdamW + Nesterov + external artifact backend + restart recovery
```

### P4 — Scale experiment

- 6 learners.
- 8 learners.
- Larger model/checkpoint pressure.
- Longer run duration.

### P5 — Pathway-lite → real operation scheduler

Add:

- operation graph
- artifact futures
- retry/resume policies
- placement policy
- cost guard
- observability/evidence package

## GitHub backup record

Initial state before commit/push:

```text
branch: codex/lambda-gpu-diloco-progress
upstream: origin/codex/lambda-gpu-diloco-progress
pre-push HEAD: 09f052121dc8cc28f9f147edaebfcf1110581697
```

Push result will be recorded in the final assistant response after the push completes.

## Latest Lambda scale experiment — 6 learners

Run ID: `lambda-sixlearner-gpu-paced-20260701144626`
Evidence root: `docs/evidence/lambda_pathway_gpu_six_learner/lambda-sixlearner-gpu-paced-20260701144626/`

Result:

```text
remote_instance_count=7
remote_process_roles=syncer + learner-0..learner-5
committed_sync_rounds=5
accepted_updates=20
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
direct_tcp_probe_passed=true
firewall_rules_restored=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
pathway_operation_layer_ready=false
billable_action_performed=true
```

A prior unpaced 6-learner attempt was blocked by Lambda/Cloudflare HTTP 429 rate limiting during rapid sequential launches. The runner now supports `--launch-delay-seconds`; the successful run used paced launches.

## Latest Lambda scale experiment — 8 learners

Run ID: `lambda-eightlearner-gpu-paced-20260701150832`
Evidence root: `docs/evidence/lambda_pathway_gpu_eight_learner/lambda-eightlearner-gpu-paced-20260701150832/`

Result:

```text
remote_instance_count=9
remote_process_roles=syncer + learner-0..learner-7
committed_sync_rounds=4
accepted_updates=24
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
direct_tcp_probe_passed=true
firewall_rules_restored=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
pathway_operation_layer_ready=false
billable_action_performed=true
```

This is now the largest live Lambda GPU Decoupled-DiLoCo proof in the repo. It still does not prove production scale because it uses the current direct-TCP/syncer object-store path, not an external durable S3-compatible backend or full scheduler.

## Latest Lambda larger-model experiment — 42k parameters

Run ID: `lambda-largermodel-42k-gpu-20260701172033`
Evidence root: `docs/evidence/lambda_pathway_gpu_larger_model/lambda-largermodel-42k-gpu-20260701172033/`

Result:

```text
model_parameters=42816
scale_vs_13216_param_baseline≈3.2x
remote_instance_count=5
remote_process_roles=syncer + learner-0..learner-3
committed_sync_rounds=4
accepted_updates=12
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
direct_tcp_probe_passed=true
firewall_rules_restored=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
pathway_operation_layer_ready=false
billable_action_performed=true
```

Blocked larger attempts:

- `lambda-largermodel-gpu-20260701153926` attempted 334,848 params and failed before recovery acceptance.
- `lambda-largermodel-85k-gpu-retry-20260701161031` and follow-ups attempted 85,504 params; runner hardening improved setup/polling, but the current direct-TCP/syncer-object-store path still showed learner reconnect/artifact availability failures around syncer restart.

Interpretation: 42k params is proven live. 85k+ params now appears to need the external durable object store and/or stronger operation-layer restart orchestration rather than more blind retries.

## Fresh verification on stop hook

Checked at: `2026-07-01T17:44:23.275896+00:00`

```text
git_status=clean
HEAD=7697612ea14c281ccde31467b97381ca229e4b9e
upstream_HEAD=7697612ea14c281ccde31467b97381ca229e4b9e
LIVE_INSTANCE_COUNT=0
LAMBDA_FILE_SYSTEM_COUNT=0
OBJECT_STORE_RELATED_ENV_KEYS=[]
S3_PREFLIGHT_STATUS=blocked
S3_PREFLIGHT_BLOCKERS=[client_not_injected]
focused_tests=31 passed
quick_profile=56 passed, 2265 deselected
py_compile=passed
ruff=passed
```

Current blocker remains external object storage: no Lambda filesystem/S3-compatible bucket is visible and no local object-store provider config is present.

## Latest Lambda S3-backed artifact experiment — 4 learners

Run ID: `lambda-s3-gpu-ca-20260702013716`
Evidence root: `docs/evidence/lambda_s3_gpu_four_learner/lambda-s3-gpu-ca-20260702013716/`

Result:

```text
artifact_storage_backend=s3_compatible
artifact_transfer_mode=object_store
remote_instance_count=5
remote_process_roles=syncer + learner-0..learner-3
committed_sync_rounds=4
accepted_updates=12
useful_tokens_accepted=512
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
direct_tcp_probe_passed=true
firewall_rules_restored=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
pathway_operation_layer_ready=false
billable_action_performed=true
```

This is the first successful live Lambda GPU run in the repo that uses the S3-compatible artifact backend. It required several fixes discovered by earlier failed attempts:

- subprocess-side S3 runtime config and explicit remote credential environment file
- boto3 installation for S3-enabled remote nodes
- replay/evidence readers that can resolve S3-compatible artifact refs
- content-addressed S3 object keys to avoid overwriting repeated artifact IDs
- rollback of Nesterov optimizer state when chunked artifact commit writing fails before a round is committed

The run is still not production-scale: it is a 4-learner proof, not an 8+ learner S3 run, not 85k+ model scale, and not a full Pathway-style scheduler.

## Latest Lambda S3-backed scale attempt — 8 learners

Run ID: `lambda-s3-eight-gpu-20260702020303`
Evidence root: `docs/evidence/lambda_s3_gpu_eight_learner/lambda-s3-eight-gpu-20260702020303/`

Result:

```text
artifact_storage_backend=s3_compatible
remote_instance_count=9
remote_process_roles=syncer + learner-0..learner-7
final_instance_count=0
status=failed
reason=all learners lost direct TCP syncer connection before recovery acceptance
```

Interpretation: the S3-backed artifact backend works and the 4-learner S3 proof passes, but combining S3 artifacts with 8 learners exposed a remaining direct-TCP/restart orchestration limit. The next fix is not more blind retrying; it is to harden the operation layer around syncer restart/readiness and learner reconnect behavior under S3-backed artifact pressure.

## Latest Lambda S3-backed scale experiment — 8 learners

Run ID: `lambda-s3-eight-gpu-hardened-20260702024523`
Evidence root: `docs/evidence/lambda_s3_gpu_eight_learner/lambda-s3-eight-gpu-hardened-20260702024523/`

Result:

```text
artifact_storage_backend=s3_compatible
artifact_transfer_mode=object_store
remote_instance_count=9
remote_process_roles=syncer + learner-0..learner-7
committed_sync_rounds=2
accepted_updates=12
useful_tokens_accepted=672
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
direct_tcp_probe_passed=true
firewall_rules_restored=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
pathway_operation_layer_ready=false
billable_action_performed=true
```

This combines the previously separate 8-learner direct-TCP proof and 4-learner S3-backed proof: 8 Lambda GPU learners now work with the S3-compatible artifact backend. It is still not production-scale because the run is short, single-region, small-model, and not managed by a full Pathway-style scheduler.

## Latest Pathway-style scheduler core and long local run

Evidence root: `docs/evidence/pathway_scheduler_long_local_no_restart/`

Result:

```text
pathway_scheduler_core=implemented
artifact_futures=true
dag_dependencies=true
retry_policy=true
fail_closed_remote_tasks=true
local_runtime_wrapped_by_scheduler=true
learners=4
steps=200
sync_rounds=26
replay_passed=true
metric_validation_passed=true
production_scale_ready=false
```

This is a real scheduler core over the local learner/syncer runtime, not a full Google Pathways clone. It adds DAG scheduling and artifact futures, but still lacks production placement, autoscaling, multi-region orchestration, and a full remote task executor.

## Latest Lambda S3-backed 42k model experiment

Run ID: `lambda-s3-42k-gpu-20260702055255`
Evidence root: `docs/evidence/lambda_s3_gpu_larger_model/lambda-s3-42k-gpu-20260702055255/`

Result:

```text
artifact_storage_backend=s3_compatible
model_parameters=42816
remote_instance_count=5
remote_process_roles=syncer + learner-0..learner-3
committed_sync_rounds=2
accepted_updates=6
useful_tokens_accepted=320
inner_optimizer_semantics=adamw
outer_optimizer_semantics=nesterov
pseudo_gradient_numeric_check_passed=true
restart_recovered=true
final_instance_count=0
lambda_l5_restart_recovery_direct_tcp_passed=true
production_scale_ready=false
```

## Latest Lambda S3-backed 85k model attempt

Run ID: `lambda-s3-85k-gpu-20260702061211`
Evidence root: `docs/evidence/lambda_s3_gpu_85k_model/lambda-s3-85k-gpu-20260702061211/`

Result:

```text
artifact_storage_backend=s3_compatible
model_parameters=85504
remote_instance_count=5
final_instance_count=0
status=failed
reason=syncer shutdown/restart failed under 85k S3 artifact pressure; learners lost direct TCP syncer connection before recovery acceptance
```

Interpretation: 85k+ model scale is still blocked. The failure is now specifically in restart/orchestration under larger S3 artifact pressure, not in basic S3 object storage or small-model training.

## Safety flags

```text
launch_ready=false
launch_allowed=false
production_scale_ready=false
```

No billable Lambda mutation was performed in this documentation/storage-bound slice.
