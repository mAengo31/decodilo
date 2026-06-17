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
