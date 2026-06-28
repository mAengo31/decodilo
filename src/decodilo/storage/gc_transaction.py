"""Transaction log and trash staging for destructive local GC."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import InvariantViolation
from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.checksums import sha256_file
from decodilo.storage.gc_accounting import build_gc_accounting_report
from decodilo.storage.reachability import build_reachability_graph
from decodilo.time_compat import UTC

GC_TRANSACTION_SCHEMA_VERSION = "v1"
TransactionState = Literal["planned", "applying", "completed", "failed", "aborted"]


class GCTransactionLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    run_id: str | None = None
    schema_version: str = GC_TRANSACTION_SCHEMA_VERSION
    planned_deletes: list[str]
    pre_delete_hashes: dict[str, str] = Field(default_factory=dict)
    delete_started_at: str | None = None
    delete_completed_at: str | None = None
    deleted_paths: list[str] = Field(default_factory=list)
    failed_deletes: dict[str, str] = Field(default_factory=dict)
    skipped_protected: list[str] = Field(default_factory=list)
    rollback_possible: bool = True
    transaction_state: TransactionState = "planned"
    trash_dir: str | None = None


def transaction_log_dir(workdir: str | Path) -> Path:
    return Path(workdir) / ".decodilo_gc_transactions"


def trash_root(workdir: str | Path) -> Path:
    return Path(workdir) / ".decodilo_trash"


def write_gc_transaction_log(path: str | Path, log: GCTransactionLog) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(log.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def load_gc_transaction_log(path: str | Path) -> GCTransactionLog:
    return GCTransactionLog.model_validate_json(Path(path).read_text(encoding="utf-8"))


def latest_gc_transactions(workdir: str | Path) -> list[GCTransactionLog]:
    root = transaction_log_dir(workdir)
    if not root.exists():
        return []
    return [load_gc_transaction_log(path) for path in sorted(root.glob("*.json"))]


def create_gc_transaction(
    *,
    workdir: str | Path,
    planned_deletes: list[str],
    run_id: str | None = None,
) -> tuple[Path, GCTransactionLog]:
    tx_id = f"gc-{uuid4().hex[:12]}"
    hashes = {
        path: sha256_file(path)
        for path in planned_deletes
        if Path(path).exists() and Path(path).is_file()
    }
    log = GCTransactionLog(
        transaction_id=tx_id,
        run_id=run_id,
        planned_deletes=planned_deletes,
        pre_delete_hashes=hashes,
        trash_dir=str(trash_root(workdir) / tx_id),
    )
    path = transaction_log_dir(workdir) / f"{tx_id}.json"
    write_gc_transaction_log(path, log)
    return path, log


def apply_gc_transaction(
    *,
    workdir: str | Path,
    planned_deletes: list[str],
    run_id: str | None = None,
    fail_after: int | None = None,
) -> GCTransactionLog:
    """Move delete candidates to trash after revalidating reachability."""

    root = Path(workdir)
    tx_path, log = create_gc_transaction(
        workdir=root,
        planned_deletes=planned_deletes,
        run_id=run_id,
    )
    started = datetime.now(UTC).isoformat()
    trash = Path(log.trash_dir or trash_root(root) / log.transaction_id)
    trash.mkdir(parents=True, exist_ok=True)
    deleted: list[str] = []
    failed: dict[str, str] = {}
    skipped: list[str] = []
    log = log.model_copy(update={"transaction_state": "applying", "delete_started_at": started})
    write_gc_transaction_log(tx_path, log)

    index = build_artifact_index(root)
    graph = build_reachability_graph(workdir=root, index=index, allow_incomplete=True)
    accounting = build_gc_accounting_report(index=index, graph=graph)
    classification = accounting.classifications

    for path_str in planned_deletes:
        item = classification.get(path_str)
        if item is not None and (
            item.reachability_state == "reachable" or item.protection_state == "protected"
        ):
            skipped.append(path_str)
            continue
        path = Path(path_str)
        if not path.exists():
            skipped.append(path_str)
            continue
        try:
            if fail_after is not None and len(deleted) >= fail_after:
                raise OSError("injected gc failure")
            relative = path.resolve().relative_to(root.resolve())
            destination = trash / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            deleted.append(path_str)
        except Exception as exc:  # noqa: BLE001 - transaction reports failure details
            failed[path_str] = str(exc)
            break

    state: TransactionState = "failed" if failed else "completed"
    completed = datetime.now(UTC).isoformat() if state == "completed" else None
    log = log.model_copy(
        update={
            "transaction_state": state,
            "delete_completed_at": completed,
            "deleted_paths": deleted,
            "failed_deletes": failed,
            "skipped_protected": skipped,
            "rollback_possible": True,
        }
    )
    write_gc_transaction_log(tx_path, log)
    if failed:
        raise InvariantViolation(f"gc transaction failed: {failed}")
    return log
