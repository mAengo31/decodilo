"""Resumable cleanup for completed GC trash transactions."""

from __future__ import annotations

import shutil
from pathlib import Path

from decodilo.storage.trash_lifecycle import (
    GCTrashCleanupReport,
    inspect_trash,
    plan_trash_cleanup,
)


def cleanup_gc_trash(
    *,
    workdir: str | Path,
    apply: bool = False,
    allow_failed_transaction_purge: bool = False,
) -> GCTrashCleanupReport:
    plan = plan_trash_cleanup(
        workdir=workdir,
        allow_failed_transaction_purge=allow_failed_transaction_purge,
    )
    index = inspect_trash(workdir)
    purged: list[str] = []
    absent: list[str] = []
    errors: list[str] = []
    bytes_purged = 0
    if apply:
        for candidate in plan.purge_candidates:
            path = Path(candidate)
            if not path.exists():
                absent.append(candidate)
                continue
            try:
                byte_size = _tree_size(path)
                shutil.rmtree(path)
                purged.append(candidate)
                bytes_purged += byte_size
            except Exception as exc:  # noqa: BLE001 - cleanup reports exact failure
                errors.append(f"{candidate}: {exc}")
    return GCTrashCleanupReport(
        dry_run=not apply,
        trash_entries_scanned=len(index.entries),
        purge_candidates=plan.purge_candidates,
        skipped_failed_transactions=plan.skipped_failed_transactions,
        bytes_purgeable=plan.bytes_purgeable,
        bytes_purged=bytes_purged,
        purged_entries=purged,
        absent_entries=absent,
        errors=errors,
        warnings=plan.warnings,
    )


def _tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

