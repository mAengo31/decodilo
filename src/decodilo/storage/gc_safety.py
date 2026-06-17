"""Validation helpers for GC safety state."""

from __future__ import annotations

from pathlib import Path

from decodilo.storage.gc_transaction import latest_gc_transactions


def failed_gc_transactions(workdir: str | Path) -> list[str]:
    return [
        tx.transaction_id
        for tx in latest_gc_transactions(workdir)
        if tx.transaction_state in {"failed", "applying", "aborted"}
    ]

