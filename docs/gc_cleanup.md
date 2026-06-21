# GC Trash Cleanup

Destructive GC moves candidates into `.decodilo_trash/<transaction_id>/`.
Milestone 014 adds inspection and resumable cleanup for that staged trash.

Inspect:

```bash
python -m decodilo.cli artifacts trash inspect \
  --workdir /tmp/decodilo-run
```

Dry run cleanup:

```bash
python -m decodilo.cli artifacts trash cleanup \
  --workdir /tmp/decodilo-run \
  --dry-run \
  --out /tmp/decodilo-run/trash_cleanup_report.json
```

Apply cleanup:

```bash
python -m decodilo.cli artifacts trash cleanup \
  --workdir /tmp/decodilo-run \
  --apply \
  --out /tmp/decodilo-run/trash_cleanup_report.json
```

Only completed GC transactions are purged by default. Failed or incomplete
transactions are skipped unless `--allow-failed-transaction-purge` is supplied.
Rerunning cleanup is idempotent: already-purged entries are not fatal.

