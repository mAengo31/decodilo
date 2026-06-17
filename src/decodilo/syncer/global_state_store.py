"""Chunked global vector artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.checksums import sha256_json
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.codec_registry import choose_artifact_codec
from decodilo.storage.tensor_artifact import read_tensor_artifact, write_tensor_artifact
from decodilo.storage.tensor_binary_format import TENSOR_BINARY_CODEC


def vector_payload(vector: np.ndarray, *, global_version: int) -> dict:
    array = np.asarray(vector, dtype=np.float64).reshape(-1)
    payload = {
        "codec_version": "v1",
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "data": array.astype(float).tolist(),
        "global_version": global_version,
    }
    payload["checksum"] = sha256_json(payload)
    return payload


def _payload_to_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_global_vector_artifact(
    *,
    vector: np.ndarray,
    run_id: str,
    global_version: int,
    artifact_id: str,
    artifact_type: str,
    transport: LocalArtifactTransport,
    manifest_path: str | Path,
    chunk_root: str | Path,
    chunk_size_bytes: int,
    created_by: str = "syncer",
    codec: str = "json_safe",
    inline_payload_max_bytes: int = 1_000_000,
) -> ArtifactRef:
    payload = vector_payload(vector, global_version=global_version)
    encoded = _payload_to_bytes(payload)
    selected_codec = choose_artifact_codec(
        codec=codec,
        payload_bytes=len(encoded),
        threshold=inline_payload_max_bytes,
    )
    if selected_codec == "binary_v1":
        return write_tensor_artifact(
            tensors={"global_vector": np.asarray(vector, dtype=np.float64).reshape(-1)},
            run_id=run_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            transport=transport,
            manifest_path=manifest_path,
            chunk_root=chunk_root,
            chunk_size_bytes=chunk_size_bytes,
            created_by=created_by,
            metadata={
                "global_version": global_version,
                "vector_checksum": payload["checksum"],
                "global_update_artifact_codec": "binary_v1",
            },
        )
    store = ChunkStore(chunk_root)
    manifest = write_binary_artifact(
        store=store,
        data=encoded,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        run_id=run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata={
            "global_version": global_version,
            "dtype": payload["dtype"],
            "shape": payload["shape"],
            "vector_checksum": payload["checksum"],
            "global_update_artifact_codec": selected_codec,
        },
        manifest_path=manifest_path,
    )
    return transport.make_ref(
        manifest=manifest,
        manifest_path=manifest_path,
        chunk_root=chunk_root,
        created_by=created_by,
    )


def read_global_vector_artifact(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
) -> tuple[np.ndarray, int]:
    manifest = transport.validate_ref(ref)
    if manifest.metadata.get("codec") == TENSOR_BINARY_CODEC:
        tensors, _ = read_tensor_artifact(ref=ref, transport=transport)
        array = np.asarray(tensors["global_vector"], dtype=np.float64).reshape(-1)
        return array, int(manifest.metadata["global_version"])
    payload = json.loads(transport.read_bytes(ref).decode("utf-8"))
    checksum = payload.get("checksum")
    payload_without_checksum = dict(payload)
    payload_without_checksum.pop("checksum", None)
    if sha256_json(payload_without_checksum) != checksum:
        raise InvariantViolation("global vector artifact checksum mismatch")
    if payload.get("codec_version") != "v1":
        raise InvariantViolation("unknown global vector artifact codec")
    array = np.asarray(payload["data"], dtype=np.float64).reshape(tuple(payload["shape"]))
    return array, int(payload["global_version"])
