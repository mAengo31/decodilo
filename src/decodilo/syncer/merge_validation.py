"""Validation helpers for binary merge artifacts."""

from __future__ import annotations

import math

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import LocalArtifactTransport
from decodilo.storage.tensor_binary_format import (
    TENSOR_BINARY_CODEC,
    TensorBinarySpec,
    tensor_metadata_from_manifest_metadata,
)


def fragment_tensor_spec(
    *,
    ref: dict,
    transport: LocalArtifactTransport,
    tensor_name: str = "fragment",
) -> TensorBinarySpec:
    manifest = transport.validate_ref(ref)
    if manifest.metadata.get("codec") != TENSOR_BINARY_CODEC:
        raise InvariantViolation("merge artifact must use tensor_binary_v1")
    metadata = tensor_metadata_from_manifest_metadata(manifest.metadata)
    for spec in metadata.tensors:
        if spec.name == tensor_name:
            return spec
    raise InvariantViolation(f"tensor {tensor_name!r} is missing from merge artifact")


def validate_merge_specs(
    *,
    refs: dict[str, dict],
    transport: LocalArtifactTransport,
    expected_shape: tuple[int, ...],
    expected_dtype: np.dtype,
) -> dict[str, TensorBinarySpec]:
    specs: dict[str, TensorBinarySpec] = {}
    for learner_id, ref in refs.items():
        spec = fragment_tensor_spec(ref=ref, transport=transport)
        if tuple(spec.shape) != expected_shape:
            raise InvariantViolation("merge artifact shape mismatch")
        if np.dtype(spec.dtype) != expected_dtype:
            raise InvariantViolation("merge artifact dtype mismatch")
        if spec.num_elements != math.prod(expected_shape):
            raise InvariantViolation("merge artifact element count mismatch")
        specs[learner_id] = spec
    return specs
