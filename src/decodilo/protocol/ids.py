"""Lightweight identifiers used across the simulation protocol."""

from __future__ import annotations

from typing import NewType

LearnerId = NewType("LearnerId", str)
FragmentId = NewType("FragmentId", str)
RoundId = NewType("RoundId", str)
CheckpointId = NewType("CheckpointId", str)


def normalize_id(value: str, *, field_name: str = "id") -> str:
    """Return a stripped identifier or raise when it cannot be logged safely."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{field_name} must not contain whitespace")
    return normalized


def make_round_id(global_version: int) -> str:
    """Create a deterministic round id from the version being committed."""

    if global_version < 0:
        raise ValueError("global_version must be non-negative")
    return f"round-{global_version + 1:08d}"

