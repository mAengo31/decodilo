# System Invariants

These invariants define the correctness boundary for the CPU-only scaffold. They
must hold before adding local multiprocessing, GPUs, networking, or Lambda
execution.

## Learner Lifecycle Invariants

- Failed learners must not process local optimizer steps.
- Paused learners must not process local optimizer steps.
- Recovered learners must record an explicit `recovery_version`.
- `local_step` must be monotonic for each learner.
- `tokens_processed` must be monotonic while a learner is alive.
- `tokens_since_last_sync` resets only after that learner's contribution is
  accepted into a committed sync round.
- Rejected contributions do not reset `tokens_since_last_sync`; the simulator
  keeps that local work visible so later accounting can distinguish processed,
  rejected, and useful tokens.

## Syncer Invariants

- `global_version` must be monotonic and increases by exactly one per committed
  sync round.
- A committed sync round must satisfy quorum unless an explicitly separate
  partial-round policy is used.
- Rejected fragments must not affect global state.
- Stale fragments must not affect global state.
- Zero-token fragments must not affect global state. The current policy rejects
  zero-token fragments.
- Quorum must not wait for all learners unless `min_quorum` is configured to
  equal the learner count.
- Failed learners must not block progress when the remaining eligible learners
  satisfy quorum.

## Replay Invariants

- Replay must reconstruct the final global vector and metrics deterministically.
- Replay must not depend on wall-clock time.
- Event order must be sufficient to reproduce the committed sync sequence.
- Event schema must be versioned. The current event schema is `v1`.
- `sync_round_started` must appear before `sync_round_committed` for the same
  round.
- Accepted learners in a committed round must have submitted fragments.
- Rejected fragments must not appear in a later committed round unless they are
  resubmitted in a new event.
- Useful-token counts in commit events must equal accepted submitted-token
  counts.
- Commit vectors must match the replay-computed token-weighted merge.

## Cost Invariants

- `total_tokens_processed` and `useful_tokens` are not assumed to be equal.
- Useful tokens are tokens accepted into committed global updates.
- Rejected tokens are tokens attached to rejected or stale fragments.
- `cost_per_total_token` and `cost_per_useful_token` are distinct metrics.
- When `useful_tokens <= total_tokens`, `cost_per_useful_token` must be greater
  than or equal to `cost_per_total_token`.
- Budget guard behavior must fail closed on missing or ambiguous pricing.
- Pricing output must show both `price_per_gpu_hour` and
  `price_per_instance_hour`, plus the basis used for the estimate.
- Safety-buffer-adjusted cost must be checked against available credits.

## Simulation Invariants

- The same seed and same config must produce the same results.
- A different seed may produce a different target vector and may produce a
  different chaos schedule once randomized chaos is added.
- Failure of one learner must not block sync if quorum is still met.
- All-but-one learner failure must stop commits when quorum is not met.
- Failed learners must not increase `tokens_processed` during failed ticks.
- Paused learners must not increase `tokens_processed` during paused ticks.
- `wasted_tokens` is defined as:

```text
total_tokens_processed - useful_tokens_accepted
```

## Transport Idempotency Invariants

- `submit_fragment` messages must include an `idempotency_key`.
- A duplicate `idempotency_key` must not double-count tokens.
- A duplicate `idempotency_key` must not apply the same delta twice.
- Duplicate transport messages may be logged, but they must not corrupt replay.
- Transport envelope serialization must be deterministic.
- Unknown schema versions and unknown message types must be rejected before use.

## Update Delivery Invariants

- Learners must not rely on arbitrary polling intervals to learn about committed
  global versions.
- A learner that applies a global update must acknowledge the applied
  `global_version`.
- The syncer must track the latest acknowledged global version per learner.
- Duplicate update acknowledgements must not move a learner version backwards or
  corrupt lag metrics.
- Update delivery events must not reference a future global version.

## Version-Lag Invariants

- Learner version lag is `current_global_version - acknowledged_global_version`
  clamped at zero.
- `learner_update_lag_current`, `learner_update_lag_max`, and
  `learner_update_lag_avg` must be derived from syncer-owned acknowledgement
  state.
- A learner that exceeds the configured lag policy may be treated as stale or
  unhealthy for quorum decisions.
- `global_update_acks` must not exceed `global_update_messages_sent`.
- Duplicate update acks must increment `duplicate_global_update_acks`, not
  `global_update_acks`.

## Backpressure Invariants

- The syncer must not allow unbounded per-learner pending messages, pending
  fragments, or inflight bytes.
- Backpressure rejection must happen before global state mutation.
- Tokens attached to a backpressure rejection must not count as useful tokens.
- Duplicate submissions after a backpressure rejection must return a duplicate
  outcome and must not create a second rejection or state update.

## Process Lifecycle Invariants

- The syncer binds to `127.0.0.1` by default.
- The local runner must wait for `syncer_ready.json` before starting learners.
- A killed learner process cannot continue processing tokens.
- A restarted learner must register and request current global state before
  training.
- Learner recovery events must include the current recovery version.
- Slow/restore chaos must be represented as explicit learner control and syncer
  events.

## Checkpoint Invariants

- Learner checkpoints must be schema-versioned.
- Checkpoint writes must be atomic: write a temp file, then rename.
- Checkpoint payloads must include a checksum.
- Corrupted checkpoints must be rejected before resume.
- A resumed learner must reconcile checkpoint global version with syncer global
  state before submitting new fragments.
- Syncer checkpoints must preserve global version, global vector, idempotency
  table, learner registry, update-stream state, metrics, and event-log position.
- Syncer checkpoints must be atomic and checksum-protected.
- Syncer recovery must reject missing, corrupted, or wrong-run checkpoints.
- A recovered syncer must not regress global version.
- Duplicate fragment submissions from before restart must remain idempotent
  after restart.
- Pending rounds are discarded on recovery unless safety can be proven.

## Heartbeat Invariants

- Heartbeat timeout detection may use monotonic wall time in the live runtime.
- Event log logical time is still assigned by the syncer and replay does not
  depend on wall time.
- Unhealthy learners must not block quorum if remaining learners satisfy
  `min_quorum`.
- If quorum is not met after a learner becomes unhealthy, the syncer must skip
  or block rounds rather than commit below quorum.

## Local Runner Cleanup Invariants

- The local runner must terminate child processes on completion or error.
- Report `process_summary` must include syncer pid, learner pids, exit codes,
  killed/restarted learners, observed unhealthy learners, and whether orphan
  cleanup was performed.
- Runtime reports must include replay validation.
- Runtime reports must include metric validation.
- Local runs must write `run_spec.json` and `artifacts.json`.

## Trainer Adapter Invariants

- Runtime process code must depend on `TrainerAdapter`, not a concrete fake
  model implementation.
- Trainers must expose local steps and token counts separately.
- Trainer state and fragments must include dtype, shape, version, and checksum.
- Trainer checkpoint/restore must recreate state exactly.
- Future trainer implementations must not require syncer protocol changes.

## State Codec Invariants

- Trainer state serialization must be deterministic.
- Codec version must be validated.

## Binary Tensor Artifact Invariants

- `tensor_binary_v1` must use raw tensor bytes plus deterministic JSON
  manifests.
- Pickle, `torch.save`, and arbitrary code execution are forbidden in the
  binary artifact path.
- Tensor names must be deterministic and unique.
- Dtype, shape, byte order, byte offset, byte length, chunk range, and tensor
  checksum must be validated before reconstruction.
- Object, ragged, unsupported, non-finite, or absurdly shaped tensors must fail
  closed.
- Event logs must contain artifact metadata, not binary tensor payloads.

## Artifact Backend Invariants

- The only enabled backend is local filesystem content-addressed storage.
- Remote backend operations must raise `RemoteBackendDisabledError`.
- Artifact refs must not use remote URLs or `file://` URLs.
- Preflight must report `remote_backend_enabled=false`.
- Range reads must validate chunk hashes and reject invalid ranges before
  returning bytes.
- Fault injection must not turn a disabled remote backend into an enabled one.

## Out-Of-Core Merge Invariants

- Numeric binary merge must be driven by a versioned `MergePlan`.
- Merge must exclude zero-token learners from token weighting.
- Merge must reject mismatched dtype, shape, element count, non-finite values
  under finite policy, and unsupported dtypes.
- `merge_peak_working_bytes_estimate` must not exceed the configured working
  budget for accepted merge plans.
- Metadata-only large-state merge must set `simulation_only=true` and
  `numeric_merge_performed=false`.

## Performance Report Invariants

- Performance counters use monotonic wall time and are not replay inputs.
- Perf report timing and byte counters must be present and nonnegative.
- Derived time fractions must be bounded to `[0, 1]`.

## Lambda Fake Lifecycle Invariants

- Fake lifecycle resources must use synthetic IDs such as `fake-i-*`.
- Real Lambda resource IDs discovered through read-only APIs must never become
  fake-created resource IDs.
- Fake lifecycle journals must include `fake_only=true`,
  `real_lambda_api_used=false`, and `billable_action_performed=false`.
- Fake launch and teardown operations must be idempotent by idempotency key and
  journal replay.
- Fake teardown verification must never emit executable real termination
  commands.
- Live read-only Lambda clients must remain unable to mutate; any mutation-shaped
  method must raise before transport.
- `launch_ready=false`, `launch_allowed=false`, and
  `billable_action_performed=false` remain required for M021 reports.
- Fake mutation-shaped API calls must reject real Lambda base URLs and API keys.
- Fake lifecycle stress must replay journals, verify teardown, run mutation
  contract checks, and preserve `real_lambda_api_used=false`.
- Real mutation absence audit must pass before fake launch readiness evidence is
  considered complete.

## Lambda Read-Only Discovery Invariants

- Real Lambda API use is limited to explicit `--api-key-file` plus
  `--live-read-only`.
- Raw API keys must not be accepted as CLI values, read from environment
  variables, printed, logged, serialized, or committed.
- Every live Lambda request must be a GET allowlisted by endpoint policy and
  mutation guard before transport.
- Launch, terminate, restart, create, delete, SSH, setup scripts, training, and
  filesystem creation remain impossible.
- Endpoint calibration may record partial read failures and schema drift, but
  it must keep `mutation=false` and `billable_action_performed=false`.
- Public Lambda discovery summaries redact resource IDs; local private reports
  may retain IDs for ledger reconciliation but must still redact secrets.
- Live ledger output is advisory only and must not contain executable
  termination instructions.
- Lambda preflight must keep `launch_ready=false` and `launch_allowed=false`.
- A normal local overhead run must include replay and metric validation status.
- Corrupted checksums must be rejected.
- Pickle and arbitrary code execution are not allowed for trainer state decode.

## Report Metric Invariants

- `useful_tokens_accepted <= total_tokens_processed`.
- `wasted_tokens = total_tokens_processed - useful_tokens_accepted`.
- `goodput_ratio` must be in `[0, 1]`.
- `global_update_broadcasts`, `global_update_messages_sent`,
  `global_update_acks`, duplicate acks, missing acks, and learner lag metrics
  have distinct meanings.

## RunSpec And Artifact Invariants

- A `RunSpec` must be stable-json serializable and hashable.
- A local report must reference the run spec path and hash.
- An artifact manifest must list expected run artifacts and hashes where
  practical.
- Missing or hash-mismatched artifacts must be reported clearly.

## Price Snapshot Invariants

- Price snapshots must include source type, source hash, capture time,
  parser version, currency, tax flag, and sample-data flag.
- Sample fixture data must not be treated as planning truth unless explicitly
  allowed.
- Stale snapshots must be rejected by default for guarded budget estimates.
- A selected price must expose `snapshot_id` and `record_id`.
- Ambiguous snapshot queries must fail closed unless explicitly allowed.

## Budget Manifest Invariants

- A run budget manifest must identify run id, mode, selected price records,
  planned instances, planned GPUs, planned hours, estimated GPU-hours, base
  cost, safety buffer, max run budget, starting credits, and projected
  remaining credits.
- A manifest that violates budget must be rejected before a run begins.
- Local runs may include manifests; future cloud runs must require manifests
  before launch.

## Optional Torch Trainer Invariants

- Torch must remain an optional dependency and must be imported lazily.
- Default installation and default tests must not require torch, CUDA, NCCL, or
  GPUs.
- Torch trainer state must be exported as CPU-portable named tensors.
- Missing, extra, shape-mismatched, corrupted, or nonfinite tensors must be
  rejected before loading state into a module.
- Token counts must be reported explicitly and must be nonnegative.
- Evaluation must not mutate model parameters.

## Optimizer Policy Invariants

- A torch trainer must report whether optimizer state is reset on global update.
- The current safe policy is reset-on-global-update by default.
- Serialized optimizer tensor state must not be claimed as supported unless a
  checksum-protected, non-pickle codec exists.
- Unsupported optimizer-state serialization must fail closed.

## Trainer Matrix Invariants

- Required trainers must pass the compatibility contract.
- Optional trainers must be reported as unavailable/skipped, not failed, when
  their optional dependency is absent.
- Matrix reports must be machine-readable and include passed, failed, skipped,
  and error details per trainer.

## Disabled Cloud Launcher Invariants

- Dry-run plans must keep `launch_allowed=false`.
- `DisabledCloudLauncher.launch()` must raise `LaunchDisabledError`.
- Launch disabled tests must pass only when launch is refused.
- No launcher path may call Lambda APIs, read cloud credentials, shell out to a
  provider CLI, or create live cloud resources.

## Teardown Plan Invariants

- Dry-run teardown plans must have `has_live_resource_ids=false`.
- Dry-run teardown plans must have an empty `live_resource_ids` list.
- A launch review checklist must include teardown expectations before any
  future launch gate can pass.
- Future real launch work must track live resource identifiers before launch is
  allowed.

## Scaling Estimator Assumptions

- Scaling estimators are deterministic calculators, not live cloud inspection.
- Bandwidth estimates model outer-loop fragments, not step-level gradients.
- Checkpoint estimates scale with retention count.
- Cost per useful token must rise as goodput decreases for fixed raw spend.

## Named Tensor Flattening Invariants

- Named tensor state must be CPU-portable at serialization time.
- Tensor names must be sorted deterministically before flattening.
- Tensor manifests must preserve dtype, shape, offset, length, and checksum.
- Manifest offsets must cover the full flat vector with no gaps or overlaps.
- Fragment layouts must not emit empty fragments.
- Corrupted tensor, flat-state, or flat-fragment checksums must be rejected.
- The syncer may merge flat numeric fragments, but the trainer owns conversion
  between named tensors and flat fragments.

## Optional Torch Dependency Invariants

- Default install and default tests must not require torch.
- Torch imports must be lazy and scoped to torch-specific helpers or trainers.
- Torch trainer checkpoints must use the safe state codec, not `torch.save` or
  pickle.
- CUDA may be used only when explicitly requested and available. No GPU is
  required for this milestone.
- No distributed PyTorch, DDP, FSDP, NCCL, or torchrun is used.

## Cloud Dry-Run Safety Invariants

- Cloud dry-run plans must never call Lambda APIs or launch resources.
- `launch_allowed` must be false for every Milestone 006 cloud plan.
- Plans must not embed secret values.
- Shape catalog entries are planning metadata only and contain no prices.
- Prices must come from versioned price snapshots.
- Sample and stale snapshots are rejected by default.
- Missing, ambiguous, or over-budget plans fail closed.

## Soak Run Invariants

- Local soak cases must run only local subprocesses.
- Each case must produce a report with replay and metric validation.
- Aggregate soak output must list passed/failed cases and report paths.
- Soak runs must clean up child processes before returning.

## Content-Addressed Storage Invariants

- Artifact chunks are addressed by SHA-256 content hash.
- A reader must validate every chunk hash before returning bytes.
- A reader must validate total artifact bytes.
- Missing or corrupted chunks must fail closed.
- Manifest JSON must be deterministic with sorted keys.
- Changing chunk hashes, metadata, or codec fields must change the manifest
  hash.
- Storage is local filesystem only in this milestone; no cloud object store
  client exists.

## Chunk Manifest Invariants

- Artifact manifests must include artifact id, type, schema version, run id,
  total bytes, chunk size, chunk hashes, root hash or manifest hash,
  compression, codec version, and metadata.
- Chunk layouts must cover the artifact byte stream in order.
- Atomic commit means chunks and manifest are written through temporary files
  before rename.
- A failed manifest commit must not create a valid committed artifact.

## Memory Budget And Spill Invariants

- Fragment storage must check declared or measured bytes before accepting a
  payload.
- Over-budget payloads must be rejected or spilled according to explicit
  policy.
- Spill must be disabled unless explicitly allowed.
- Spill budget exhaustion must reject the fragment before global state
  mutation.
- Memory and spill rejections must not count as useful tokens.
- Spill files retained after a run must be referenced by artifacts; otherwise
  cleanup may remove them.

## Streaming Checkpoint Invariants

- Chunked checkpoints must reference artifact manifests rather than embedding
  large binary state.
- Restore must validate referenced artifact chunks before accepting checkpoint
  state.
- Corrupted or missing checkpoint artifacts must fail closed.
- Existing small JSON checkpoints remain valid for tiny tests, but chunked
  checkpoints must preserve the same run id, component id, global version, and
  checksum semantics.

## Streaming Merge Invariants

- Numeric streaming merge must match the existing in-memory token-weighted SGD
  merge within floating-point tolerance for small arrays.
- Fragment sizes and checksums must be validated before merge.
- Streaming merge metrics must record bytes read, bytes written, chunks
  processed, and peak working-byte estimate.
- Metadata-only large-state merge is a dry-run lineage check and must be
  labeled as such; it is not a numeric training update.

## Preflight Invariants

- Local preflight must validate RunSpec, ArtifactManifest, artifact hashes, and
  report validation when present.
- Cloud preflight must validate dry-run plan, budget identifiers, teardown
  plan, launch review artifact, and disabled launcher status.
- Preflight must not call cloud APIs or launch anything.
- Cloud preflight must report `launch_allowed=false`.
- Hash mismatches or missing required artifacts must fail closed.

## Live Chunked Runtime Invariants

- `payload_storage_mode=chunked` must submit learner fragments as artifact
  references, not inline vectors.
- `payload_storage_mode=auto` must switch to artifact references when payload
  size exceeds `inline_payload_max_bytes`.
- Chunked event payloads must include artifact id, manifest hash, payload bytes,
  storage kind, dtype/shape metadata, and content checksum; they must not embed
  chunk bytes, base64 payloads, or giant arrays.
- The syncer must validate artifact refs before accepting a fragment.
- Artifact validation failures must not mutate global state or count as useful
  tokens.
- Duplicate idempotency keys must not re-read, re-store, or re-apply the same
  artifact payload.

## Artifact Reference Invariants

- Artifact refs are local filesystem references only in this milestone.
- Manifest paths and chunk roots must stay inside the configured workdir or
  artifact root.
- Path traversal, URL-like paths, outside-workdir absolute paths, missing
  manifests, missing chunk roots, corrupt hashes, and symlink escapes must fail
  closed.
- No remote artifact backend, network fetch, cloud storage client, or shell
  command may be used to resolve an artifact ref.

## Chunked Merge And Update Invariants

- `merge_mode=streaming_chunked` requires chunked or auto payload storage.
- Numeric streaming merge must match in-memory token-weighted merge for the same
  accepted fragments and token weights.
- Zero-token learners must have zero numerical effect in streaming merge.
- Metadata-only merge must be marked `simulation_only=true` and
  `numeric_merge_performed=false`.
- Chunked global updates must be delivered as artifact refs when
  `global_update_storage_mode=chunked`.
- Learners must validate and apply a chunked global update before sending
  `global_update_ack`.

## Chunked Recovery Invariants

- `checkpoint_storage_mode=chunked` must recover the syncer from the chunked
  checkpoint artifact as the primary source.
- Chunked mode must not silently fall back to an inline checkpoint.
- `checkpoint_storage_mode=dual` may write both formats, but the recovery source
  must be explicit in the report and recovery event.
- Recovered syncer state must preserve global version, global vector,
  idempotency table, committed round metadata, learner registry state, metrics,
  and logical time continuity.
- Replay must reject chunked numeric logs when referenced artifacts are missing
  or corrupt.

## Milestone 012 Lifecycle Invariants

- Idempotency compaction must never remove in-flight records, the latest
  recovery window, or records needed for duplicate suppression since the latest
  replay snapshot.
- Expired duplicate submissions must be rejected as expired duplicates, not
  silently treated as new useful-token contributions.
- Event segment manifests must form a verifiable hash chain. Missing or
  corrupted segments must fail replay unless replay starts from a valid later
  snapshot.
- Replay snapshots must be hash-validated and must reject run-id mismatch,
  tail-chain mismatch, or global-version regression.
- Recovery manifests must name the checkpoint/replay/artifact inputs required
  for restart and must prevent silent fallback to older checkpoints.
- Global-state lifecycle policy must protect the latest global state and any
  state referenced by checkpoints, replay snapshots, or in-flight learner
  updates.
- Artifact GC is dry-run by default and must never delete run specs, final
  reports, latest recovery manifests, latest recovery checkpoints, latest
  global states, or retained snapshot/checkpoint artifacts.
- Checkpoint lifecycle may make old checkpoints GC-eligible only when they are
  not needed by recovery or replay snapshot policy.

## Milestone 013 Lifecycle Stress Invariants

- Repeated checkpoint, compaction, replay snapshot, recovery-manifest, artifact
  audit, and GC-plan cycles must preserve recovery correctness.
- Genesis replay and snapshot-plus-tail replay must agree on final global
  version and accepted useful tokens.
- Lifecycle stress reports must surface validation errors instead of masking
  them.

## Recovery Manifest Chain Invariants

- `recovery_manifest.json` is the active pointer to the latest recovery
  manifest.
- Versioned recovery manifests must form a hash chain through
  `previous_recovery_manifest_hash`.
- Chain validation must reject missing previous manifests, hash mismatches,
  run-id mismatch, global-version regression, and stale active pointers.
- Chunked recovery must load the checkpoint artifact named by the recovery
  manifest, not a mutable fallback path.

## Artifact Audit Invariants

- Every artifact referenced by a report, event log, replay snapshot, recovery
  manifest, compact report, GC plan, or artifact manifest must exist and remain
  inside the run workdir.
- Hash-mismatched tracked artifacts fail audit.
- Artifact manifests generated by compact or lifecycle commands must be tracked
  in `artifacts.json`.

## GC Accounting And Transaction Invariants

- Reachability categories are disjoint:
  `reachable + unreachable + unresolved == unique_artifacts_scanned`.
- Protection is an overlay on reachability and must be explained, not counted
  as a separate partition.
- GC remains dry-run by default.
- Destructive GC must write a transaction log and re-validate reachability
  before moving delete candidates.
- Referenced chunks and protected run artifacts must never be deleted.
- Failed GC transactions must be detected by run validation.

## Milestone 014 Performance And Cleanup Invariants

- Performance reports may use monotonic wall time, but replay must not depend
  on wall time.
- Timing fields that were not measured must be `null`, not silently reported as
  zero.
- Fraction fields must stay in `[0, 1]` when present.
- Bottleneck rankings must be stable for equal values.
- Performance and preflight reports must keep `launch_ready=false` and
  `launch_allowed=false`.
- Trash cleanup is dry-run by default and only purges completed GC transaction
  trash unless explicitly overridden.
- Trash cleanup must be idempotent after repeated or interrupted cleanup runs.
- Hardware probing is local and informational; CUDA/MPS timing requires
  `--allow-accelerator` and must not initialize distributed torch.

## Milestone 014A Learner Scaling Invariants

- Learner scaling commands are planning or local calibration only; they must not
  call cloud APIs, use credentials, launch instances, or require GPUs.
- Scaling scenarios must reject nonpositive learner counts, invalid quorum
  policies, negative token/failure rates, and nonpositive configured bandwidth
  caps.
- Goodput estimates must distinguish raw allocation from accepted useful
  contribution.
- Algorithmic efficiency is labeled as a heuristic proxy and must not be
  presented as a model-quality guarantee.
- Pod-count recommendations must explain the selected candidate and dominant
  bottleneck.
- Candidates exceeding configured artifact, bandwidth, or syncer caps must be
  rejected rather than silently recommended.
- Scaling decision reports must keep `launch_ready=false` and
  `launch_allowed=false`.

## Milestone 015 Remote Backend Design Invariants

- Remote backend requirements are derived from learner-scaling targets before
  any real backend implementation is considered.
- The local simulator must not perform network calls or read credentials.
- Disabled remote backend operations must raise clearly.
- Simulator success is not production proof and must not enable a remote
  backend.
- Remote backend design reports must keep `remote_backend_enabled=false`,
  `launch_ready=false`, and `launch_allowed=false`.
- Future remote backends must prove conditional manifest put, content-hash
  validation, scoped authorization, lifecycle policy, delete transaction logs,
  replay/checkpoint compatibility, and cost/bandwidth accounting before launch
  can be reconsidered.

## Milestone 016 Remote Backend Readiness Invariants

- The readiness gate cannot emit SDK-addition or real-backend-enabled statuses
  in Milestone 016.
- Simulator conformance is review evidence only.
- Evidence packages hash every referenced artifact.
- Credential models accept symbolic references only and reject raw secrets.
- Provider matrices are manual-only and `is_live_validated=false`.
- `remote_backend_enabled=false`, `launch_ready=false`, and
  `launch_allowed=false` remain enforced.

## Milestone 017 Remote Backend Review Invariants

- Implementation proposals are review-only and cannot import or validate SDKs.
- SDK guard failures block review progress.
- Critical open risks block SDK review.
- Rollout phases after `phase_0_design_only` are plan text only.
- Decision records cannot emit `sdk_addition_allowed_by_policy`,
  `real_backend_enabled`, `launch_ready`, or `launch_allowed`.
- Review packages hash referenced artifacts and keep backend/launch flags false.

## Milestone 018 Lambda Boundary Invariants

- Lambda fixture models may preserve unknown fields as metadata, but must not
  preserve raw secrets.
- Disabled Lambda clients must not perform reads or mutations.
- Read-only Lambda clients must use fake transport only.
- Mutation guard allowlists known reads and denies all mutations and unknowns.
- Credential models accept symbolic API-key refs only and reject raw-looking
  keys or secret field names.
- Resource ledger reconciliation must not launch or terminate resources.
- Lambda launch and teardown plans are dry-run artifacts and cannot execute.
- Lambda discovery reports must keep `live_api_used=false`.
- Lambda preflight must keep `launch_ready=false` and `launch_allowed=false`.

## Milestone 019 Lambda Live Read-Only Invariants

- A real Lambda API key may be read only from an explicit `--api-key-file`.
- Raw `--api-key` CLI values are not accepted.
- Lambda credential environment variables are not read.
- Live transport requires explicit `--live-read-only`.
- Live transport only sends GET requests with no request body.
- Endpoint policy denies all non-GET, unknown, and mutating endpoints.
- Read-only audit must show zero mutating operations and no secret leakage.
- Live resource ledger must not suggest executable termination.
- Live preflight remains non-launchable with `launch_ready=false` and
  `launch_allowed=false`.

## Milestone 020 Lambda Reconciliation Invariants

- M020 reconciliation reads existing discovery, audit, ledger, launch-plan,
  teardown-plan, price-snapshot, and approval artifacts only.
- Shape matching and price reconciliation must not call live pricing APIs or
  Lambda APIs.
- The default first-launch policy is one instance, 30 minutes, and a $50 max
  budget.
- Approval manifests may approve only a future fake launch lifecycle in M020;
  they do not enable launch.
- `future_real_launch_candidate` remains false.
- Launch blocker reports must keep disabled launch code and current-milestone
  launch prohibition as blockers.
- `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `mutating_operations=0` remain
  enforced.

## Milestone 023 Lambda Mutation Boundary Invariants

- M023 artifacts are proposal/spec/safety-case evidence only.
- Future mutation operations may be named as metadata, but every future mutation
  must keep `allowed_in_m023=false`.
- The arming gate is `design_only` and cannot set `armed=true`.
- Kill-switch and termination verification designs must not contain executable
  terminate commands.
- Review records may reach `design_review_ready`, but cannot approve launch or
  enable real mutation.
- `real_mutation_enabled=false`, `launch_ready=false`,
  `launch_allowed=false`, and `billable_action_performed=false` remain
  enforced.

## Milestone 024 Lambda Disabled Mutation Skeleton Invariants

- Disabled real mutation transport methods must raise before request
  construction, credential access, or network access.
- Request builder output is review-only: no executable URL, method, or body.
- Feature flags and arming state cannot be enabled by config, CLI, environment,
  approval artifacts, or tests.
- Execution guard can pass review-only checks but must always keep
  `execution_guard_passed_for_execution=false`.
- Budget locks, idempotency plans, and resource scopes are evidence artifacts
  only and cannot enable launch.
- Skeleton audit passing means "mutation skeleton present but disabled"; it is
  not launch readiness.
- `real_mutation_enabled=false`, `mutation_armed=false`,
  `launch_ready=false`, `launch_allowed=false`, and
  `billable_action_performed=false` remain enforced.

## Milestone 025 Lambda Final Prelaunch Review Invariants

- Final prelaunch evidence packages and reviews are review-only.
- The go/no-go record may only emit `no_go`, `blocked`, or
  `go_for_future_m026_real_launch_review`.
- First-launch and termination runbooks must be non-executable.
- Operator checklist completion cannot enable launch.
- Semantic mutation audit must pass before any future review candidate status.
- No source path may emit enabled launch or mutation flags.
- `real_mutation_enabled=false`, `launch_ready=false`,
  `launch_allowed=false`, and `billable_action_performed=false` remain
  enforced.

## Milestone 026 Lambda Decision Gate Invariants

- M026 may only decide `blocked`, `needs_more_evidence`, or
  `approve_m027_minimal_real_mutation_implementation`.
- The positive M026 decision authorizes M027 implementation work only, not
  launch execution.
- Human review acknowledgements and one-instance, 30-minute, $50 limits must be
  validated before M027 authorization.
- Freshness evidence can require more evidence without mutating Lambda.
- The blocker matrix may clear M027 implementation blockers while still keeping
  real-launch execution blockers present.
- M027 authorization records cannot authorize execution, launch, termination,
  restart, SSH, setup scripts, training, or spend.
- `real_mutation_enabled=false`, `launch_ready=false`,
  `launch_allowed=false`, and `billable_action_performed=false` remain
  enforced.

## Milestone 027 Lambda Minimal Mutation Invariants

- Minimal mutation request construction may target only fake-server execution.
- Fake-server execution requires localhost or in-memory fake transport,
  fake-server mode, M027 authorization, endpoint policy, mutation guard, budget
  lock, idempotency, resource scope, teardown, and termination verification
  evidence.
- Real Lambda URLs and credentials must be rejected before execution.
- Fake launch and fake terminate operations must be idempotent by key and use
  only synthetic `fake-i-*` resource IDs.
- Response parsing must reject real API usage, real billable action claims, and
  non-synthetic resource IDs.
- The live Lambda client remains read-only.
- `real_mutation_enabled=false`, `launch_ready=false`,
  `launch_allowed=false`, and `billable_action_performed=false` remain
  enforced.

## Milestone 028 Lambda Final Authorization Invariants

- M028 may authorize only
  `authorized_for_m029_one_instance_launch_attempt`.
- Fresh read-only refresh, if run, must use GET/read-only operations and report
  `mutating_operations=0`.
- Final budget lock must keep one instance, 30 minutes, and 50 USD limits.
- Final resource lock must reject unmanaged billable resources and unowned
  termination scope.
- Launch-window lock must require an operator and forbid background execution.
- M029 authorization package can authorize only the next milestone; it cannot
  authorize launch now.
- Final no-mutation audit must pass before M028 decision can authorize M029.
- `real_mutation_enabled=false`, `launch_ready=false`,
  `launch_allowed=false`, and `billable_action_performed=false` remain
  enforced.

## Milestone 029 Lambda First Launch Invariants

- M029 may send at most one real launch request and one owned-instance
  terminate request after all gates pass.
- M029 must verify termination through Lambda read-only get/list. OS shutdown
  is insufficient.
- M029 must not restart, create/delete keys or filesystems, SSH, run setup
  scripts, run cloud-init, run training, or terminate unowned resources.
- If launch succeeds or may have succeeded, termination verification is
  mandatory and manual review is required when verification cannot complete.
- The run report must finish with `launch_ready=false` and
  `launch_allowed=false`.
## M029B Shape Evidence

M029B distinguishes public product catalog evidence from live availability. An empty
Lambda instance-type discovery response is inconclusive unless endpoint semantics are
known. Non-sample price evidence may resolve a planned shape for future review, but
M029B never launches, terminates, mutates, or spends.

## Milestone 029D Incident Closeout Invariants

- A lost launch response blocks a second launch attempt until an incident report
  closes as `closed_no_instance_visible` or
  `closed_manual_termination_verified`.
- M029D must not launch, restart, create/delete resources, SSH, run setup
  scripts, train, or perform automatic termination.
- Manual console confirmation is required to close an ambiguous launch incident
  when no owned instance ID was recorded.
- Automation may terminate only an exact or high-confidence owned instance and
  must never terminate ambiguous or unowned candidates.
- Lost launch responses must not trigger automatic launch retry.
  `launch_ready=false` and `launch_allowed=false` remain enforced.
## Lambda M030 Second-Attempt Review

- M030 must not launch, terminate, mutate, SSH, run setup scripts, train, or
  spend.
- A closed M029C incident is required before second-attempt authorization.
- Response-loss mitigation, correlation, and reconciliation plans are required.
- M030 may authorize only `authorized_for_future_m031_second_launch_attempt`.
- `launch_ready=false`, `launch_allowed=false`, and
  `billable_action_performed=false` remain enforced.

## Lambda M031D Repeated Response-Loss Closeout

- M031D must not launch, automatically terminate, restart, create/delete
  resources, SSH, run setup scripts, train, or perform new billable mutation.
- M031 incident closeout requires manual console confirmation plus read-only
  discovery evidence.
- Closing the M031 incident clears only the incident-local blocker.
- Two lost launch responses activate a global future-launch hold until repeated
  response-loss mitigation is accepted and fresh operator approval is obtained.
- Future launch hold reports must keep `launch_ready=false` and
  `launch_allowed=false`.

## Lambda M032 Response-Loss Mitigation

- M032 must not launch, terminate, or send real mutation requests.
- HTTP response capture must record status and redacted response metadata before
  parsing.
- Offline response-loss regression fixtures must cover timeout, empty body,
  non-JSON body, malformed/schema failure, and HTTP error cases.
- Future launch hold release is for future review only and must keep
  `launch_ready=false` and `launch_allowed=false`.

## Lambda M033 Third-Attempt Review

- M033 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, or spend.
- Endpoint-spec operator confirmation is required, and medium confidence must
  be explicitly accepted.
- Response-capture settings and timeout policy must be locked before future
  M034 review authorization.
- The third-attempt correlation plan must use a new idempotency key distinct
  from M029C and M031.
- The reconciliation plan must forbid automated termination for medium, low, or
  no-confidence candidates.
- M033 may authorize only `authorized_for_future_m034_third_launch_attempt`.
- `launch_ready=false`, `launch_allowed=false`, `real_mutation_enabled=false`,
  and `billable_action_performed=false` remain enforced.

## Lambda M034A Third-Attempt Gate Wiring

- M034A must not launch, terminate, send real mutation requests, SSH, run setup
  scripts, train, or spend.
- `lambda m029 run` must accept explicit M033/M034 artifact flags for a future
  third attempt and block before request construction when any required artifact
  is missing or invalid.
- The M034 gate must enforce endpoint confirmation, response-capture lock,
  launch timeout policy, risk review, correlation plan, reconciliation plan,
  M034 authorization, third go/no-go, and M033 report.
- The effective launch timeout must come from the timeout policy and be at least
  30 seconds; the historical 10 second transport default cannot satisfy M034.
- Response capture must be active, capture status before parse, redact headers,
  capture content type/body size metadata, and keep body samples disabled unless
  explicitly justified by a future review.
- The launch idempotency key must match the third-attempt correlation plan, and
  automatic launch retry must remain forbidden.
- The reconciliation plan must prevent automated termination for medium, low, or
  no-confidence candidates.
- M034A gate reports and run reports must keep `launch_ready=false`,
  `launch_allowed=false`, `real_mutation_enabled=false`, and
  `billable_action_performed=false` unless a later real launch milestone actually
  sends a launch request.

## Lambda M035 Post-Incident Launch Strategy

- M035 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, or spend.
- M035 must represent all three ambiguous real launch attempts before producing
  a strategy decision.
- Endpoint confidence review must account for repeated response loss and must
  not silently upgrade medium confidence to high.
- Lower-cost shape strategy may recommend future reauthorization, but it must
  not change the active launch shape or enable execution.
- Support/operator evidence requests must contain no secrets and perform no
  Lambda API calls.
- M035 decision records may authorize only future milestone paths; they must not
  emit `launch_now`, `execute_now`, `launch_ready=true`, or
  `launch_allowed=true`.

## Lambda M036 Support Confirmation And Shape Reauthorization

- M036 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, or spend.
- M036 support confirmation requests and responses must contain no API keys,
  Authorization headers, bearer tokens, or other secret-like values.
- Endpoint confidence may upgrade to high only when launch and terminate
  method/path, response shape, ambiguous-response semantics, and termination
  verification semantics are all answered.
- Missing ambiguous launch behavior must block validation after the three
  response-loss incidents.
- Lower-cost shape review may recommend reauthorization, but it must not switch
  the active launch shape or enable execution.
- M036 strategy decisions may authorize only future review paths; they must not
  emit `launch_now`, `execute_now`, `launch_ready=true`, or
  `launch_allowed=true`.

## Lambda M037 Support Response Ingestion

- M037 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, or spend.
- M037 must not fabricate support/operator answers. If the support response is
  absent, endpoint confidence cannot upgrade.
- Support response ingestion must reject API keys, Authorization headers, bearer
  tokens, passwords, private keys, and other secret-like values.
- Endpoint confidence can upgrade only when complete support evidence confirms
  endpoint behavior and ambiguous-response semantics.
- Lower-cost shape selection must not switch active launch artifacts; it can
  only require future reauthorization.
- M037 decisions may authorize only future review paths; they must not emit
  `launch_now`, `execute_now`, `launch_ready=true`, or `launch_allowed=true`.

## Lambda M036R Strand CLI Compatibility Audit

- M036R must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- Strand-AI `lambda-cli` evidence is unofficial behavioral evidence only, even
  when operator-tested successfully.
- Strand compatibility must keep `launch_ready=false`, `launch_allowed=false`,
  `real_mutation_enabled=false`, and `billable_action_performed=false`.
- Strand-compatible launch payloads require `region_name`,
  `instance_type_name`, `ssh_key_names`, and `quantity=1`; setup scripts,
  cloud-init, user data, and training payload fields remain forbidden.
- Strand-compatible terminate payloads use `instance_ids` and may treat 2xx
  empty response bodies as request success, but termination still requires
  read-only verification in any future launch milestone.
- Endpoint confidence must not be represented as official Lambda support
  confirmation solely because it matches the unofficial CLI.

## Lambda M037R Lower-Cost Strand Reauthorization

- M037R must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- `gpu_1x_h100_pcie` lower-cost plans must use the Strand payload keys
  `region_name`, `instance_type_name`, `ssh_key_names`, and `quantity=1`.
- M037R may select only existing SSH key names from read-only discovery or an
  operator-selected existing key; it must not create, delete, modify, or expose
  SSH key material.
- Lower-cost price reconciliation must use non-sample catalog evidence and keep
  the planned 30 minute cost under the $50 budget.
- Empty or inconclusive instance-type discovery must not be treated as proof of
  unavailability; live availability remains unknown until a future launch.
- M037R decisions may authorize only future review paths and must keep
  `launch_ready=false`, `launch_allowed=false`, `real_mutation_enabled=false`,
  and `billable_action_performed=false`.

## Lambda M038 Lower-Cost M039 Authorization Review

- M038 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- Fresh read-only discovery may be used, but it must report
  `mutating_operations=0` and `billable_action_performed=false`.
- Lower-cost canonical readiness must require an existing SSH key selection,
  Strand-compatible `quantity=1` payload, non-sample price reconciliation, and
  zero unmanaged billable resources.
- M039 authorization is future-only. It must not emit `launch_now`,
  `execute_now`, `launch_ready=true`, or `launch_allowed=true`.
- Operator approval templates must not be treated as actual approval unless all
  required acknowledgements are explicitly complete.
- Command previews must remain non-executable.

## Lambda M038A Lower-Cost Future Approval

- M038A must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- Completed lower-cost operator approval may authorize only a future M039 review;
  it must not set `launch_ready=true`, `launch_allowed=true`, or
  `real_mutation_enabled=true`.
- The approval must acknowledge `gpu_1x_h100_pcie`, `us-west-1`, one instance,
  $50 budget, 30 minute runtime, existing SSH key attachment without SSH use,
  no setup/cloud-init/training, no restart/create/delete, no automatic launch
  retry, owned termination, and read-only termination verification.
- A passing M039 authorization or gate-check remains future-only. M039 must
  still collect supervised launch confirmation before any billable operation.
- M039 command previews must stay `executable=false`.

## Lambda M039A Lower-Cost Execution Wiring

- M039A must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- `lambda m029 run` must accept explicit lower-cost M039 flags. If any such
  flag is present, all lower-cost artifacts are required before request
  construction.
- The lower-cost path must prove `selected_shape=gpu_1x_h100_pcie`,
  `selected_region=us-west-1`, `quantity=1`, Strand payload compatibility,
  response capture, status-before-parse, 30 second timeout, and
  `no_auto_launch_retry=true`.
- The old M028/M029 `gpu_8x_h100_sxm` resource path must not be used as a
  fallback when lower-cost flags are present.
- The selected existing SSH key raw name may be used only from the private local
  SSH selection artifact during request construction. Public reports must store
  only hash/redacted SSH key values and no SSH key material.
- Fake-server lower-cost launch/terminate tests may exercise the execution path;
  real Lambda API calls remain forbidden in M039A tests.

## Lambda M040 Capacity Closeout and Availability-First Review

- M040 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend beyond
  optional read-only discovery.
- A structured 400 capacity error with no owned instance ID and zero post-run
  visible/unmanaged instances may close as
  `closed_capacity_unavailable_no_instance_created`.
- Capacity errors are not response-loss incidents and are not teardown failures.
- Same fixed-shape retry is blocked unless fresh availability evidence changes
  and a future operator explicitly accepts the risk.
- Availability-first selection must treat empty/inconclusive instance-type
  discovery as `endpoint_inconclusive`, not proof of live availability.
- Availability-first selection must not preselect a fixed GPU shape; it must
  rank all approved, non-sample-priced, Strand-compatible quantity-1 candidates
  by live availability, buffered 30-minute cost, single-GPU preference,
  no-filesystem requirement, and Strand-compatible payload.
- Catalog-only candidates may be ranked for planning, but they require future
  operator risk acceptance before any billable attempt; without that acceptance,
  `launch_selection_allowed=false`.
- M040 authorization and go/no-go records are future-review only and must keep
  `launch_ready=false`, `launch_allowed=false`, `real_mutation_enabled=false`,
  and `billable_action_performed=false`.

## Lambda M041 Catalog Availability Risk Decision

- M041 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- Catalog-only availability risk must be explicitly accepted or declined by the
  operator; M041 must not silently choose either path.
- Accepted catalog-only risk can authorize only a future M042 review with
  `authorized_for_future_m042_catalog_availability_launch_review`.
- Declined catalog-only risk must produce a wait-for-live-availability plan.
- M042 command previews from M041 must remain non-executable.
- All M041 artifacts must keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## Lambda M043 Capacity Follow-Up and Rotation Review

- M043 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend beyond
  optional read-only discovery.
- Repeated 400 capacity errors for the same shape must be detected and must
  block silent same-shape retry by default.
- A 400 JSON insufficient-capacity response with no owned instance ID and final
  discovery counts of zero maps to `capacity_rejected_no_instance_created`, not
  a teardown incident.
- Catalog candidate rotation may rank alternatives for a future review, but
  catalog evidence is not live availability proof.
- M043 decisions may authorize only a future catalog-candidate rotation review,
  wait-for-live-availability path, operator-selected alternative-shape review,
  or pause. They must not emit `launch_now`, `execute_now`,
  `launch_ready=true`, or `launch_allowed=true`.

## Lambda M044 Catalog Rotation Operator Decision

- M044 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend beyond
  optional read-only discovery.
- M044 must not silently choose an operator outcome. Without explicit
  acceptance, wait, or manual-selection input, the decision remains incomplete.
- Accepting `gpu_8x_a100_80gb_sxm4` can authorize only a future M045 catalog
  rotation launch review.
- Declining the selected candidate must produce either a wait-for-live-
  availability path or a manual-candidate-selection path.
- M045 command previews from M044 must remain non-executable.
- All M044 artifacts must keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## Lambda M044G Flexible Selector Future Review

- M044G must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend beyond
  optional read-only discovery.
- Flexible-selector authorization must derive the selected shape from selector
  output only. Fixed-shape M039/M045 artifacts must not be accepted as the
  selected-shape source.
- Catalog-only selector output must require explicit catalog-only risk
  acceptance before it can be authorized for future review.
- Flexible-selector command previews must remain non-executable and must not
  include raw SSH key names.
- All M044G artifacts must keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## Lambda M044H Capacity-History-Aware Flexible Selector

- M044H must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend beyond
  optional read-only discovery.
- Recent capacity-failed shapes must be excluded by default unless fresh live
  availability evidence proves the shape is available now.
- Generic catalog-only risk acceptance must not override recent capacity
  history. Same-shape capacity retry requires a separate explicit acceptance
  artifact.
- Future authorization must derive the selected candidate from the
  capacity-history-aware selector output.
- Capacity-history command previews must remain non-executable.
- All M044H artifacts must keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## Lambda M045 Capacity-Selected Future Review

- M045 must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- M045 requires an explicit operator decision for the
  capacity-history-selected candidate. Without approval, wait, or manual
  selection, the decision remains incomplete.
- Accepted approval can authorize only a future M046 capacity-selected launch
  review.
- Declined approval must produce either a wait-for-live-availability path or a
  manual-candidate-selection path.
- M046 command previews from M045 must remain non-executable and must not
  include raw SSH key names.
- All M045 artifacts must keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## Lambda M046A Capacity-Selected Execution Wiring

- M046A must not launch, terminate, mutate Lambda resources, SSH, run setup
  scripts, train, send real POST/PUT/PATCH/DELETE requests, or spend.
- `lambda m029 run` must accept explicit M046 capacity-selected artifact flags.
  If any M046 flag is present, the command must require the full M046 artifact
  set before request construction.
- The M046 path must use the selected candidate from capacity-aware selector and
  M046 authorization artifacts. For the current approved path this is
  `gpu_8x_a100_80gb_sxm4`.
- Old M028/M029 fallback and M039 lower-cost fallback must be blocked when M046
  flags are present.
- Raw SSH key names may be read only from the private SSH key selection artifact
  for request construction. Public reports must use only hash/redacted values.
- M046A reports and command previews must keep `launch_ready=false`,
  `launch_allowed=false`, `billable_action_performed=false`, and
  `real_mutation_enabled=false`.
## Lambda M047 Lifecycle Smoke Closeout

- M047 is closeout-only: it must not launch, terminate, create, delete, SSH, run setup
  scripts, use cloud-init, train, or send mutating Lambda requests.
- Historical M046C `billable_action_performed=true` may be recorded only as historical
  evidence; M047 artifacts keep `billable_action_performed=false`.
- Live Lambda shape selection must use canonical live instance type ids from
  `/instance-types`; stale aliases such as `gpu_8x_a100_sxm_80gb` must resolve to
  `gpu_8x_a100_80gb_sxm4` before any future launch review.
- Launch regions for future lifecycle smoke attempts must come from fresh read-only live
  availability evidence for the selected shape.
- `launch_ready=false`, `launch_allowed=false`, and `real_mutation_enabled=false` remain
  invariant across M047 closeout, parser, region-selection, alias, price-join, strategy,
  and aggregate report artifacts.

## M048 Test Profiles

- M048 must not launch, terminate, mutate Lambda resources, call live Lambda APIs, require
  `.env`, or spend money.
- Full pytest remains the safety source of truth; quick profile changes must not remove
  safety tests from the full suite.
- The quick profile is opt-in via the `quick` marker and must exclude `lambda_live`,
  `lambda_real_mutation`, `subprocess_heavy`, `launch_history_heavy`, lifecycle, perf,
  soak, integration, slow, and optional hardware tests.
- Lambda offline tests must be marked `lambda_offline` and must not call live Lambda or
  require real credentials.
- Real Lambda mutation belongs in guarded CLI/operator flows, not default pytest.
- M048 reports keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## M049A Runtime Flake Handling

- M049A must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, or spend money.
- `test_local_recovery_after_kill` remains in full and `runtime_local` profiles and
  remains excluded from quick through `subprocess_heavy`.
- Runtime recovery tests must prefer event-driven conditions over unbounded sleeps.
- Bounded retry, if introduced later, must be opt-in, subprocess-specific, and report
  attempts plus the first failure summary. It must not hide repeated failures.
- M049A keeps `launch_ready=false`, `launch_allowed=false`, and
  `billable_action_performed=false`.

## M050 Remote Runtime Bootstrap Planning

- M050 must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, SSH, run remote commands, install packages, or train.
- The default future M051 bootstrap mode is metadata-only. SSH is declined unless a
  separate SSH approval artifact explicitly authorizes connectivity or a single
  allowlisted command for a later supervised milestone.
- SSH key attachment for a Lambda launch payload never implies SSH usage approval.
- Package installation and training remain denied by default.
- M051 authorization is future-review only. Runbook previews are non-executable.
- M050 artifacts keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## M051A Metadata Bootstrap One-Shot Arming

- M051A must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, SSH, run remote commands, install packages, train, or spend.
- Standing M050/M051 artifacts must remain durable and non-executable:
  `launch_ready=false`, `launch_allowed=false`, and `launch_authorized_now=false`.
- One-shot arming is ephemeral, expires, is limited to one launch request-send attempt,
  forbids automatic retry, and requires owned termination plus read-only termination
  verification if an instance is created.
- `one_shot_request_send_permitted=true` may appear only in the M051 execution reviewer
  bridge. The arming artifact binds evidence but does not expose request-send
  permission.
- M051B execution flags must include the one-shot arming, reviewer bridge, artifact
  binding, and arming gate artifacts. Missing or expired bridge evidence halts before
  request construction.
- M051A artifacts keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## M052 Metadata Bootstrap Closeout

- M052 must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, SSH, run remote commands, install packages, train, or spend.
- M052 records M051B as historical evidence only. M052 artifacts keep
  `billable_action_performed=false`; historical M051B evidence may record
  `historical_billable_action_performed=true`.
- Metadata bootstrap closeout succeeds only when owned termination is verified, final
  discovery shows zero visible/unmanaged instances, no secrets are present, and no SSH,
  remote command, package install, or training attempt occurred.
- SSH key attachment for the provider launch payload remains distinct from SSH usage.
- M053 next-step decisions may authorize planning for a future SSH-connectivity review
  only; they must not authorize SSH, commands, launch, or training now.

## M053 SSH Connectivity Planning

- M053 must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, SSH, open network connections to instances, run remote commands, transfer
  files, forward ports, install packages, train, or spend.
- SSH-connectivity-only means a future bounded handshake/authentication review, not an
  interactive shell, remote command, file transfer, forwarding, package install, setup,
  cloud-init, or training.
- Existing SSH key references may be carried by hash/redaction only. Private key material
  and raw public key material must never be serialized.
- Missing operator approval keeps M054 `not_authorized`; complete approval may authorize
  only a future M054 review and must not authorize SSH now.
- M053 artifacts keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## M054A SSH Connectivity Execution Packaging

- M054A must not launch, terminate, mutate Lambda resources, call live Lambda APIs, use
  credentials, SSH, open network connections, run remote commands, transfer files,
  forward ports, install packages, train, or spend.
- M054A may define only a future M054B execution package for one supervised lifecycle
  launch plus one bounded SSH connectivity/authentication probe.
- The SSH client command artifact is a redacted, non-executable preview. It must use
  safe OpenSSH options such as `BatchMode=yes`, `RequestTTY=no`,
  `ClearAllForwardings=yes`, `ForwardAgent=no`, `ForwardX11=no`,
  `PermitLocalCommand=no`, `ControlMaster=no`, `SessionType=none`, bounded timeouts,
  and `-N`; it must not include a remote command.
- File transfer tools and port-forwarding flags remain forbidden: no `scp`, `sftp`,
  `rsync`, `-L`, `-R`, `-D`, agent forwarding, or X11 forwarding.
- Private key material and raw public key material must never be serialized. M054A may
  carry only a redacted symbolic private-key reference for future operator review.
- One-shot arming remains ephemeral and non-executable. Request-send and SSH-probe
  permission may appear only in the reviewer bridge, and only for future M054B review.
- M054A artifacts keep `launch_ready=false`, `launch_allowed=false`,
  `billable_action_performed=false`, and `real_mutation_enabled=false`.

## M055 SSH Host Discovery Fix

- M054B must be closed out honestly as lifecycle-successful but
  SSH-host-discovery-blocked when launch and owned termination succeed but no
  provider-visible host/IP is discovered.
- SSH key attachment or selection does not prove SSH connectivity and must not be
  used to hide host-discovery failure.
- M055 host discovery may inspect provider list/detail metadata only through the
  existing gated lifecycle path. Public artifacts may store sanitized metadata key
  names and paths, but not raw private key material or secrets.
- If no host/IP is discovered, the SSH probe must not open a socket and the owned
  instance must still be terminated and verified.
- Private/non-global IPs are rejected by default unless an explicit private-network
  SSH policy is enabled.
- `LAMBDA_SSH_HOST_OVERRIDE` is an explicit operator fallback only and must be
  reported as such.
- M055 keeps remote commands, command output collection, file transfer, port
  forwarding, package installation, setup scripts, cloud-init, and training
  forbidden.
