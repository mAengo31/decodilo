"""Synthetic large model-state source without full allocation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.errors import ChunkCorruptionError
from decodilo.trainer.chunked_state import (
    ChunkedStateChunk,
    LazyTensorSpec,
    make_chunked_state_manifest,
)


class SyntheticLargeStateSource:
    """Generates deterministic logical model-state chunks on demand."""

    def __init__(
        self,
        *,
        run_id: str,
        learner_id: str,
        seed: int,
        tensor_name: str = "weights",
        logical_parameter_count: int,
        bytes_per_parameter: int = 2,
        global_version: int = 0,
    ) -> None:
        if logical_parameter_count <= 0:
            raise ValueError("logical_parameter_count must be positive")
        if bytes_per_parameter <= 0:
            raise ValueError("bytes_per_parameter must be positive")
        self.run_id = run_id
        self.learner_id = learner_id
        self.seed = seed
        self.tensor_name = tensor_name
        self.logical_parameter_count = logical_parameter_count
        self.bytes_per_parameter = bytes_per_parameter
        self.global_version = global_version
        self.total_logical_bytes = logical_parameter_count * bytes_per_parameter
        self._bytes_materialized = 0

    @property
    def bytes_materialized(self) -> int:
        return self._bytes_materialized

    def manifest(self):
        spec = LazyTensorSpec(
            name=self.tensor_name,
            dtype=f"synthetic_bytes_{self.bytes_per_parameter}",
            shape=[self.logical_parameter_count],
            offset_bytes=0,
            length_bytes=self.total_logical_bytes,
            bytes_per_element=self.bytes_per_parameter,
            logical_num_elements=self.logical_parameter_count,
        )
        return make_chunked_state_manifest(
            run_id=self.run_id,
            learner_id=self.learner_id,
            global_version=self.global_version,
            tensors=[spec],
            metadata={
                "seed": self.seed,
                "synthetic": True,
                "bytes_per_parameter": self.bytes_per_parameter,
            },
        )

    def _chunk_bytes(self, *, chunk_index: int, size: int) -> bytes:
        prefix = (
            f"{self.run_id}:{self.learner_id}:{self.tensor_name}:"
            f"{self.seed}:{chunk_index}:"
        ).encode()
        output = bytearray()
        counter = 0
        while len(output) < size:
            output.extend(hashlib.sha256(prefix + counter.to_bytes(8, "big")).digest())
            counter += 1
        data = bytes(output[:size])
        self._bytes_materialized += len(data)
        return data

    def iter_fragments(self, *, max_fragment_bytes: int) -> Iterator[ChunkedStateChunk]:
        if max_fragment_bytes <= 0:
            raise ValueError("max_fragment_bytes must be positive")
        offset = 0
        chunk_index = 0
        while offset < self.total_logical_bytes:
            size = min(max_fragment_bytes, self.total_logical_bytes - offset)
            data = self._chunk_bytes(chunk_index=chunk_index, size=size)
            yield ChunkedStateChunk(
                tensor_name=self.tensor_name,
                chunk_index=chunk_index,
                logical_offset_bytes=offset,
                length_bytes=size,
                data=data,
                checksum=sha256_bytes(data),
            )
            offset += size
            chunk_index += 1


def verify_synthetic_chunk(chunk: ChunkedStateChunk) -> None:
    if sha256_bytes(chunk.data) != chunk.checksum:
        raise ChunkCorruptionError("synthetic large-state chunk checksum mismatch")
