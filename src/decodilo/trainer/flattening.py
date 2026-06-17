"""Flatten and fragment named tensor model state."""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.errors import InvariantViolation
from decodilo.trainer.named_state import (
    NamedTensorState,
    named_state_from_numpy,
    tensor_array,
    validate_named_state,
)
from decodilo.trainer.tensor_manifest import (
    FragmentCodecMetadata,
    TensorManifest,
    sha256_json,
    validate_manifest,
)

FLAT_STATE_SCHEMA_VERSION = "v1"


class FlatState(BaseModel):
    """Flat numeric view of a named tensor state."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = FLAT_STATE_SCHEMA_VERSION
    global_version: int = Field(ge=0)
    values: list[float]
    manifest: TensorManifest
    checksum: str

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != FLAT_STATE_SCHEMA_VERSION:
            raise ValueError(f"unknown flat state schema {value!r}")
        return value


class FlatFragment(BaseModel):
    """Contiguous fragment of a flat model state."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = FLAT_STATE_SCHEMA_VERSION
    fragment_id: int = Field(ge=0)
    global_version: int = Field(ge=0)
    offset: int = Field(ge=0)
    length: int = Field(gt=0)
    data: list[float]
    manifest_checksum: str
    checksum: str


class FragmentLayout(BaseModel):
    """Deterministic coverage plan for flat fragments."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = FLAT_STATE_SCHEMA_VERSION
    total_elements: int = Field(ge=0)
    spans: list[dict[str, int]]
    checksum: str


def flat_state_checksum_payload(
    *,
    global_version: int,
    values: list[float],
    manifest: TensorManifest,
) -> dict[str, Any]:
    return {
        "schema_version": FLAT_STATE_SCHEMA_VERSION,
        "global_version": global_version,
        "values": values,
        "manifest_checksum": manifest.checksum,
    }


def flatten_named_state(state: NamedTensorState) -> FlatState:
    """Flatten tensors by sorted manifest order into a 1D float vector."""

    validate_named_state(state)
    values: list[float] = []
    for spec in state.manifest.tensors:
        array = tensor_array(state, spec.name)
        values.extend(np.asarray(array).reshape(-1).astype(float).tolist())
    payload = flat_state_checksum_payload(
        global_version=state.global_version,
        values=values,
        manifest=state.manifest,
    )
    return FlatState(
        global_version=state.global_version,
        values=values,
        manifest=state.manifest,
        checksum=sha256_json(payload),
    )


def validate_flat_state(flat_state: FlatState) -> None:
    if flat_state.schema_version != FLAT_STATE_SCHEMA_VERSION:
        raise InvariantViolation(f"unknown flat state schema {flat_state.schema_version!r}")
    validate_manifest(flat_state.manifest)
    if len(flat_state.values) != flat_state.manifest.total_elements:
        raise InvariantViolation("flat state length does not match manifest")
    expected = sha256_json(
        flat_state_checksum_payload(
            global_version=flat_state.global_version,
            values=flat_state.values,
            manifest=flat_state.manifest,
        )
    )
    if expected != flat_state.checksum:
        raise InvariantViolation("flat state checksum mismatch")


def reconstruct_named_state(flat_state: FlatState) -> NamedTensorState:
    """Reconstruct named tensors from a flat vector and manifest."""

    validate_flat_state(flat_state)
    flat_values = np.asarray(flat_state.values, dtype=np.float64)
    tensors: dict[str, np.ndarray] = {}
    for spec in flat_state.manifest.tensors:
        start = spec.offset
        stop = start + spec.length
        values = flat_values[start:stop].astype(np.dtype(spec.dtype), copy=True)
        tensors[spec.name] = values.reshape(spec.shape)
    state = named_state_from_numpy(
        tensors,
        global_version=flat_state.global_version,
        device="cpu",
    )
    validate_named_state(state)
    return state


def make_fragment_layout(
    *,
    total_elements: int,
    num_fragments: int | None = None,
    max_elements_per_fragment: int | None = None,
) -> FragmentLayout:
    """Create deterministic non-empty fragment spans covering the flat vector."""

    if total_elements <= 0:
        raise ValueError("total_elements must be positive")
    if num_fragments is None and max_elements_per_fragment is None:
        raise ValueError("num_fragments or max_elements_per_fragment is required")
    if num_fragments is not None and num_fragments <= 0:
        raise ValueError("num_fragments must be positive")
    if max_elements_per_fragment is not None and max_elements_per_fragment <= 0:
        raise ValueError("max_elements_per_fragment must be positive")

    if max_elements_per_fragment is not None:
        count = int(np.ceil(total_elements / max_elements_per_fragment))
    else:
        assert num_fragments is not None
        count = min(num_fragments, total_elements)
    count = max(1, min(count, total_elements))

    base = total_elements // count
    remainder = total_elements % count
    offset = 0
    spans: list[dict[str, int]] = []
    for fragment_id in range(count):
        length = base + (1 if fragment_id < remainder else 0)
        spans.append({"fragment_id": fragment_id, "offset": offset, "length": length})
        offset += length
    layout_payload = {
        "schema_version": FLAT_STATE_SCHEMA_VERSION,
        "total_elements": total_elements,
        "spans": spans,
    }
    return FragmentLayout(
        total_elements=total_elements,
        spans=spans,
        checksum=sha256_json(layout_payload),
    )


def validate_fragment_layout(layout: FragmentLayout) -> None:
    if layout.schema_version != FLAT_STATE_SCHEMA_VERSION:
        raise InvariantViolation(f"unknown fragment layout schema {layout.schema_version!r}")
    expected = sha256_json(
        {
            "schema_version": FLAT_STATE_SCHEMA_VERSION,
            "total_elements": layout.total_elements,
            "spans": layout.spans,
        }
    )
    if expected != layout.checksum:
        raise InvariantViolation("fragment layout checksum mismatch")
    offset = 0
    for span in layout.spans:
        if span["offset"] != offset:
            raise InvariantViolation("fragment layout has gap or overlap")
        if span["length"] <= 0:
            raise InvariantViolation("fragment layout contains empty fragment")
        offset += span["length"]
    if offset != layout.total_elements:
        raise InvariantViolation("fragment layout does not cover flat state")


def fragment_checksum_payload(fragment: FlatFragment) -> dict[str, Any]:
    payload = fragment.model_dump(mode="json")
    payload.pop("checksum", None)
    return payload


def make_flat_fragment(
    *,
    fragment_id: int,
    global_version: int,
    offset: int,
    data: list[float],
    manifest_checksum: str,
) -> FlatFragment:
    payload = {
        "schema_version": FLAT_STATE_SCHEMA_VERSION,
        "fragment_id": fragment_id,
        "global_version": global_version,
        "offset": offset,
        "length": len(data),
        "data": data,
        "manifest_checksum": manifest_checksum,
    }
    return FlatFragment(**payload, checksum=sha256_json(payload))


def fragment_flat_state(flat_state: FlatState, layout: FragmentLayout) -> list[FlatFragment]:
    validate_flat_state(flat_state)
    validate_fragment_layout(layout)
    if layout.total_elements != len(flat_state.values):
        raise InvariantViolation("fragment layout size does not match flat state")
    fragments: list[FlatFragment] = []
    for span in layout.spans:
        start = span["offset"]
        stop = start + span["length"]
        fragments.append(
            make_flat_fragment(
                fragment_id=span["fragment_id"],
                global_version=flat_state.global_version,
                offset=start,
                data=flat_state.values[start:stop],
                manifest_checksum=flat_state.manifest.checksum,
            )
        )
    return fragments


def validate_flat_fragment(fragment: FlatFragment) -> None:
    if fragment.schema_version != FLAT_STATE_SCHEMA_VERSION:
        raise InvariantViolation(f"unknown flat fragment schema {fragment.schema_version!r}")
    if fragment.length <= 0 or len(fragment.data) != fragment.length:
        raise InvariantViolation("flat fragment length mismatch")
    if sha256_json(fragment_checksum_payload(fragment)) != fragment.checksum:
        raise InvariantViolation("flat fragment checksum mismatch")


def assemble_flat_fragments(
    *,
    fragments: list[FlatFragment],
    manifest: TensorManifest,
    global_version: int,
) -> FlatState:
    if not fragments:
        raise ValueError("fragments must not be empty")
    validate_manifest(manifest)
    ordered = sorted(fragments, key=lambda fragment: fragment.offset)
    values: list[float] = []
    expected_offset = 0
    for fragment in ordered:
        validate_flat_fragment(fragment)
        if fragment.manifest_checksum != manifest.checksum:
            raise InvariantViolation("flat fragment manifest checksum mismatch")
        if fragment.global_version != global_version:
            raise InvariantViolation("flat fragment global version mismatch")
        if fragment.offset != expected_offset:
            raise InvariantViolation("flat fragments have gap or overlap")
        values.extend(fragment.data)
        expected_offset += fragment.length
    if expected_offset != manifest.total_elements:
        raise InvariantViolation("flat fragments do not cover full manifest")
    payload = flat_state_checksum_payload(
        global_version=global_version,
        values=values,
        manifest=manifest,
    )
    return FlatState(
        global_version=global_version,
        values=values,
        manifest=manifest,
        checksum=sha256_json(payload),
    )


def fragment_codec_metadata(
    fragments: list[FlatFragment],
    manifest: TensorManifest,
) -> FragmentCodecMetadata:
    return FragmentCodecMetadata(
        manifest_checksum=manifest.checksum,
        fragment_count=len(fragments),
        total_elements=manifest.total_elements,
    )
