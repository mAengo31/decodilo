"""Artifact serialization helpers for trainer fragments."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.codec_registry import choose_artifact_codec
from decodilo.storage.tensor_artifact import read_tensor_artifact, write_tensor_artifact
from decodilo.storage.tensor_binary_format import TENSOR_BINARY_CODEC
from decodilo.trainer.state import TrainerFragment
from decodilo.trainer.state_codec import make_fragment, validate_fragment


def fragment_to_bytes(fragment: TrainerFragment) -> bytes:
    return (
        json.dumps(fragment.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_fragment_artifact(
    *,
    fragment: TrainerFragment,
    transport: LocalArtifactTransport,
    manifest_path: str | Path,
    chunk_root: str | Path,
    chunk_size_bytes: int,
    created_by: str,
    codec: str = "json_safe",
    inline_payload_max_bytes: int = 1_000_000,
) -> ArtifactRef:
    validate_fragment(fragment)
    payload = fragment_to_bytes(fragment)
    selected_codec = choose_artifact_codec(
        codec=codec,
        payload_bytes=len(payload),
        threshold=inline_payload_max_bytes,
    )
    artifact_id = (
        f"{fragment.run_id}:{fragment.learner_id}:"
        f"fragment-{fragment.fragment_id}:v-{fragment.global_version}"
    )
    metadata = {
        "fragment_id": fragment.fragment_id,
        "global_version": fragment.global_version,
        "tokens": fragment.tokens,
        "trainer_state_kind": fragment.trainer_state_kind,
        "dtype": fragment.dtype,
        "shape": fragment.shape,
        "checksum": fragment.checksum,
        "fragment_codec": selected_codec,
    }
    if selected_codec == "binary_v1":
        return write_tensor_artifact(
            tensors={"fragment": np.asarray(fragment.data, dtype=np.dtype(fragment.dtype))},
            run_id=fragment.run_id,
            artifact_id=artifact_id,
            artifact_type="trainer_fragment",
            transport=transport,
            manifest_path=manifest_path,
            chunk_root=chunk_root,
            chunk_size_bytes=chunk_size_bytes,
            created_by=created_by,
            metadata={
                **metadata,
                "trainer_type": fragment.trainer_type,
                "learner_id": fragment.learner_id,
                "run_id": fragment.run_id,
            },
        )
    store = ChunkStore(chunk_root)
    manifest = write_binary_artifact(
        store=store,
        data=payload,
        artifact_id=artifact_id,
        artifact_type="trainer_fragment",
        run_id=fragment.run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata=metadata,
        manifest_path=manifest_path,
    )
    return transport.make_ref(
        manifest=manifest,
        manifest_path=manifest_path,
        chunk_root=chunk_root,
        created_by=created_by,
    )


def read_fragment_artifact(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
) -> TrainerFragment:
    manifest = transport.validate_ref(ref)
    if manifest.metadata.get("codec") == TENSOR_BINARY_CODEC:
        tensors, _ = read_tensor_artifact(ref=ref, transport=transport)
        metadata = manifest.metadata
        array = np.asarray(tensors["fragment"], dtype=np.dtype(str(metadata["dtype"])))
        learner_id = (
            str(metadata["learner_id"])
            if "learner_id" in metadata
            else (str(ref["created_by"]) if isinstance(ref, dict) else ref.created_by)
        )
        fragment = make_fragment(
            trainer_type=str(metadata.get("trainer_type", "numpy_convex")),
            run_id=manifest.run_id,
            learner_id=learner_id,
            fragment_id=int(metadata["fragment_id"]),
            global_version=int(metadata["global_version"]),
            data=array,
            tokens=int(metadata["tokens"]),
            trainer_state_kind=str(metadata.get("trainer_state_kind", "flat")),
        )
        validate_fragment(fragment)
        return fragment
    data = transport.read_bytes(ref)
    fragment = TrainerFragment.model_validate_json(data.decode("utf-8"))
    validate_fragment(fragment)
    return fragment
