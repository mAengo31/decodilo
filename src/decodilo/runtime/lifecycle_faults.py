"""Small local lifecycle fault helpers for tests."""

from __future__ import annotations

from pathlib import Path


def corrupt_text_file(path: str | Path, marker: str = "corrupted") -> None:
    target = Path(path)
    target.write_text(marker, encoding="utf-8")


def remove_file(path: str | Path) -> None:
    Path(path).unlink(missing_ok=True)

