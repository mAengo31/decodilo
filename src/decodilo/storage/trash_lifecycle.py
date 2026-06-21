"""Inspect staged GC trash without deleting retained artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.gc_transaction import latest_gc_transactions, trash_root


class GCTrashEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    transaction_state: str
    trash_dir: str
    exists: bool
    file_count: int
    byte_size: int


class GCTrashIndex(BaseModel):
    model_config = ConfigDict(frozen=True)

    workdir: str
    entries: list[GCTrashEntry] = Field(default_factory=list)


class GCTrashCleanupPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run: bool = True
    purge_candidates: list[str] = Field(default_factory=list)
    skipped_failed_transactions: list[str] = Field(default_factory=list)
    bytes_purgeable: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class GCTrashCleanupReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run: bool
    trash_entries_scanned: int
    purge_candidates: list[str] = Field(default_factory=list)
    skipped_failed_transactions: list[str] = Field(default_factory=list)
    bytes_purgeable: int = 0
    bytes_purged: int = 0
    purged_entries: list[str] = Field(default_factory=list)
    absent_entries: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def inspect_trash(workdir: str | Path) -> GCTrashIndex:
    root = Path(workdir)
    entries: list[GCTrashEntry] = []
    known = {tx.transaction_id: tx.transaction_state for tx in latest_gc_transactions(root)}
    trash = trash_root(root)
    if trash.exists():
        for path in sorted(item for item in trash.iterdir() if item.is_dir()):
            count, size = _tree_stats(path)
            entries.append(
                GCTrashEntry(
                    transaction_id=path.name,
                    transaction_state=known.get(path.name, "unknown"),
                    trash_dir=str(path),
                    exists=True,
                    file_count=count,
                    byte_size=size,
                )
            )
    for transaction_id, state in sorted(known.items()):
        if any(entry.transaction_id == transaction_id for entry in entries):
            continue
        entries.append(
            GCTrashEntry(
                transaction_id=transaction_id,
                transaction_state=state,
                trash_dir=str(trash / transaction_id),
                exists=False,
                file_count=0,
                byte_size=0,
            )
        )
    return GCTrashIndex(workdir=str(root), entries=entries)


def plan_trash_cleanup(
    *,
    workdir: str | Path,
    allow_failed_transaction_purge: bool = False,
) -> GCTrashCleanupPlan:
    index = inspect_trash(workdir)
    candidates: list[str] = []
    skipped: list[str] = []
    bytes_purgeable = 0
    for entry in index.entries:
        if not entry.exists:
            continue
        if entry.transaction_state == "completed" or allow_failed_transaction_purge:
            candidates.append(entry.trash_dir)
            bytes_purgeable += entry.byte_size
        else:
            skipped.append(entry.transaction_id)
    return GCTrashCleanupPlan(
        dry_run=True,
        purge_candidates=candidates,
        skipped_failed_transactions=skipped,
        bytes_purgeable=bytes_purgeable,
    )


def write_trash_index(path: str | Path, index: GCTrashIndex) -> None:
    _write_json(path, index.model_dump(mode="json"))


def write_trash_cleanup_report(path: str | Path, report: GCTrashCleanupReport) -> None:
    _write_json(path, report.model_dump(mode="json"))


def _tree_stats(path: Path) -> tuple[int, int]:
    count = 0
    size = 0
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
            size += item.stat().st_size
    return count, size


def _write_json(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

