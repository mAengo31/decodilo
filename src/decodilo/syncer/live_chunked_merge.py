"""Live merge helpers for chunked trainer fragment artifacts."""

from __future__ import annotations

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.syncer.streaming_merge import StreamingMergeResult, streaming_token_weighted_merge
from decodilo.trainer.fragment_artifacts import read_fragment_artifact


def live_streaming_merge_from_artifacts(
    *,
    global_values: np.ndarray,
    fragment_refs: dict[str, ArtifactRef | dict],
    token_counts: dict[str, int],
    transport: LocalArtifactTransport,
    outer_lr: float = 1.0,
    chunk_elements: int = 1024,
) -> StreamingMergeResult:
    learner_values = {
        learner_id: np.asarray(
            read_fragment_artifact(ref=ref, transport=transport).data,
            dtype=np.float64,
        )
        for learner_id, ref in fragment_refs.items()
    }
    return streaming_token_weighted_merge(
        global_values=global_values,
        learner_values=learner_values,
        token_counts=token_counts,
        outer_lr=outer_lr,
        chunk_elements=chunk_elements,
    )

