# Run Reproducibility

Milestone 005 adds machine-readable run specifications and artifact manifests.

## RunSpec

`RunSpec` is the canonical typed config for a run. It records run id, mode,
seed, learner count, steps, quorum settings, vector/fragments, trainer type,
heartbeat/update/backpressure settings, chaos plan, checkpoint settings, optional
pricing manifest, code version, and creation time.

Local runs write `workdir/run_spec.json` and include its SHA-256 in the report.

## Artifact Manifest

`workdir/artifacts.json` records the run spec, report, event log, syncer
checkpoint, learner checkpoints, learner logs, price snapshots, and optional
budget manifest. Hashes are recorded where practical.

The CLI can validate a workdir manifest:

```bash
python -m decodilo.cli local artifacts /tmp/decodilo-local
```

## Report Validation

Reports include metric validation status. The CLI can validate an existing
report:

```bash
python -m decodilo.cli local validate-report /tmp/decodilo-local/report.json
```

## Determinism

The single-process simulator is deterministic for the same seed and config.
The local multiprocess runtime writes the same RunSpec, but process scheduling
can affect message ordering and therefore exact bitwise results. Reports should
not overclaim determinism beyond what the runtime can guarantee.

## Milestone 006 Additions

Named tensor manifests and flat fragments use stable JSON checksums, so model
state reconstruction is auditable. Cloud dry-run plans include a RunSpec hash
when a run spec is supplied. Local soak runs write per-case reports plus an
aggregate `soak_summary.json` that references the report artifacts.

## Milestone 007 Additions

Trainer runs add trainer type, state kind, state byte estimate, parameter
count, final trainer loss when available, nonfinite status, and trainer
checkpoint paths to reports. Metric validation rejects reports that claim
nonfinite trainer state for accepted normal runs or report a non-positive state
byte estimate.

Trainer compatibility matrix reports and soak profile summaries are
machine-readable JSON artifacts so optional trainer behavior is auditable.

## Milestone 008 Additions

Chunked artifact manifests make larger checkpoints auditable without embedding
large binary payloads in reports or event logs. Artifact readers verify chunk
hashes and total byte counts before returning payload data.

Preflight reports capture whether run specs, artifact manifests, dry-run plans,
budget data, teardown plans, and launch reviews are present and consistent.
Performance counters are written to reports for diagnosis, but they are not
replayable logical state and should not be used to prove deterministic replay.

## Milestone 009 Additions

RunSpec records payload, checkpoint, merge, and global-update storage modes.
Chunked live runs retain artifact refs in event logs and manifests so replay can
validate numeric state from referenced local artifacts. Multiprocess scheduling
can still change exact quorum composition, so byte-for-byte final vectors are
only expected when the accepted fragments and ordering are identical.

## Milestone 012 Additions

Long runs can now write segmented event logs and replay snapshots. A replay can
start from genesis or from a validated snapshot plus later event segments. The
report and run lifecycle commands state which artifacts were checked.

Recovery manifests identify the checkpoint, event segments, replay snapshot,
global state refs, and artifact hashes required to restart or validate a run.
Run compaction is non-destructive: it can write replay snapshots, close or
rotate event segments, compact idempotency metadata, and produce a GC plan, but
it does not delete artifacts.

Useful commands:

```bash
python -m decodilo.cli run inspect --workdir /tmp/decodilo-run
python -m decodilo.cli run validate --workdir /tmp/decodilo-run
python -m decodilo.cli run compact --workdir /tmp/decodilo-run --out /tmp/decodilo-run/compact_report.json
```

## Milestone 013 Additions

Lifecycle stress repeatedly runs compaction, replay snapshot creation, dry-run
GC planning, artifact auditing, and validation against the same local workdir.
Recovery manifests form a hash chain, and `recovery validate-chain` rejects
missing predecessors, hash mismatches, run-id mismatch, and global-version
regression.

Artifact audits check every generated manifest/report/snapshot/checkpoint for
missing, untracked, checksum-mismatched, or outside-workdir references.
