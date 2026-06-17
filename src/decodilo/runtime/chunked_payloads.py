"""Shared helpers for chunked runtime payloads."""

from __future__ import annotations

from pathlib import Path


def chunk_size_bytes_from_mb(chunk_size_mb: int) -> int:
    if chunk_size_mb <= 0:
        raise ValueError("chunk_size_mb must be positive")
    return chunk_size_mb * 1024 * 1024


def default_artifact_root(workdir: str | Path) -> Path:
    return Path(workdir) / "artifacts"


def default_chunk_store_root(workdir: str | Path) -> Path:
    return Path(workdir) / "artifacts" / "store"

