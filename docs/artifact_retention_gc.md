# Artifact Retention And GC

Artifact garbage collection is reachability based and dry-run first.

The reachability graph is built from:

- `run_spec.json`
- `report.json`
- `artifacts.json`
- `recovery_manifest.json`
- event segment manifests
- replay snapshots
- checkpoint and global-state manifests
- explicitly retained artifact records

Artifacts are classified as live, protected, retained, temporary, orphaned, or deleted.
The GC plan may mark temporary or orphaned files as reclaimable, but it must never delete
the run spec, final report, latest recovery manifest, latest recovery checkpoint, latest
global state, or artifacts referenced by retained snapshots and checkpoints.

`decodilo artifacts gc-plan` is non-destructive. `decodilo artifacts gc --apply` is required
for deletion and still protects required artifacts.

## Milestone 013 Accounting And Transactions

GC accounting now reports disjoint reachability counts separately from policy
overlays:

```text
reachable_count + unreachable_count + unresolved_count
  == unique_artifacts_scanned
```

Protection is an overlay, usually a subset of reachable artifacts. Retention
labels explain whether an artifact is retained, GC-eligible, temporary,
orphaned, or deleted. Reports include `overlaps_explained` so counts such as
protected and reachable are not accidentally added together.

Destructive GC uses a transaction log. Before applying deletes, it re-validates
reachability and refuses to delete artifacts that became reachable after the
plan was created. Delete candidates are moved into `.decodilo_trash/` under a
transaction id. Failed or interrupted transactions remain visible to
`run validate`.

## Milestone 014 Trash Cleanup

Trash cleanup is separate from GC. It is dry-run by default and only purges
trash directories for completed GC transactions unless
`--allow-failed-transaction-purge` is supplied.

```bash
python -m decodilo.cli artifacts trash inspect --workdir /tmp/decodilo-run

python -m decodilo.cli artifacts trash cleanup \
  --workdir /tmp/decodilo-run \
  --dry-run \
  --out /tmp/decodilo-run/trash_cleanup_report.json
```

Cleanup is resumable and idempotent. Retained artifacts outside
`.decodilo_trash/` must never be deleted by trash cleanup.
