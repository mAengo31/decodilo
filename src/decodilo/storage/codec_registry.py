"""Artifact codec registry."""

from __future__ import annotations

SUPPORTED_ARTIFACT_CODECS = {"json_safe", "binary_v1", "auto"}


def validate_artifact_codec(codec: str) -> str:
    if codec not in SUPPORTED_ARTIFACT_CODECS:
        raise ValueError(f"invalid artifact codec {codec!r}")
    return codec


def choose_artifact_codec(*, codec: str, payload_bytes: int, threshold: int) -> str:
    validate_artifact_codec(codec)
    if codec == "auto":
        return "binary_v1" if payload_bytes > threshold else "json_safe"
    return codec
