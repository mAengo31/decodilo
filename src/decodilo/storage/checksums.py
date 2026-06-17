"""Checksum and stable serialization helpers for storage artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def stable_json_bytes(data: Any) -> bytes:
    return stable_json(data).encode("utf-8")


def sha256_json(data: Any) -> str:
    return sha256_bytes(stable_json_bytes(data))


def iter_file_chunks(path: str | Path, *, chunk_size_bytes: int = 1024 * 1024) -> Iterable[bytes]:
    with Path(path).open("rb") as handle:
        yield from iter(lambda: handle.read(chunk_size_bytes), b"")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    for chunk in iter_file_chunks(path):
        digest.update(chunk)
    return digest.hexdigest()
