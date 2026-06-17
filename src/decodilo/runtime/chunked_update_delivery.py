"""Chunked global update delivery helpers."""

from __future__ import annotations

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.syncer.global_state_store import read_global_vector_artifact


def apply_update_ref_to_vector(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
) -> tuple[np.ndarray, int]:
    return read_global_vector_artifact(ref=ref, transport=transport)

