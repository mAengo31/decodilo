"""Safe torch module state conversion through NamedTensorState."""

from __future__ import annotations

from typing import Any

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import FlatState, flat_state_checksum_payload, validate_flat_state
from decodilo.trainer.named_state import (
    NamedTensorState,
    named_state_from_numpy,
    tensor_array,
    validate_named_state,
)
from decodilo.trainer.tensor_manifest import sha256_json
from decodilo.trainer.torch_metrics import tensor_is_finite
from decodilo.trainer.torch_optional import require_torch


def module_to_named_state(module: Any, *, global_version: int) -> NamedTensorState:
    """Export a torch module state_dict as CPU numpy-backed named tensors."""

    tensors: dict[str, np.ndarray] = {}
    for name, tensor in module.state_dict().items():
        if not tensor_is_finite(tensor):
            raise InvariantViolation(f"non-finite tensor in module state: {name}")
        tensors[name] = tensor.detach().cpu().numpy().copy()
    return named_state_from_numpy(tensors, global_version=global_version, device="cpu")


def load_named_state_into_module(
    module: Any,
    state: NamedTensorState,
    *,
    strict: bool = True,
) -> None:
    """Load NamedTensorState into a torch module with strict checks."""

    torch = require_torch()
    validate_named_state(state)
    module_state = module.state_dict()
    expected_names = set(module_state)
    actual_names = set(state.tensors)
    missing = expected_names - actual_names
    extra = actual_names - expected_names
    if strict and missing:
        raise InvariantViolation(f"missing tensors: {sorted(missing)}")
    if strict and extra:
        raise InvariantViolation(f"extra tensors: {sorted(extra)}")
    update: dict[str, Any] = {}
    for name in sorted(expected_names & actual_names):
        target = module_state[name]
        array = tensor_array(state, name)
        if list(target.shape) != list(array.shape):
            raise InvariantViolation(f"shape mismatch for {name}")
        if not np.isfinite(array).all():
            raise InvariantViolation(f"non-finite tensor in named state: {name}")
        try:
            tensor = torch.tensor(array, dtype=target.dtype, device=target.device)
        except Exception as exc:  # noqa: BLE001 - dtype/device compatibility failure
            raise InvariantViolation(f"dtype incompatible for {name}: {exc}") from exc
        update[name] = tensor
    module.load_state_dict(update, strict=strict)


def flat_vector_to_named_state_for_module(
    module: Any,
    *,
    values: list[float],
    global_version: int,
) -> NamedTensorState:
    """Reconstruct a module-shaped NamedTensorState from a flat vector."""

    module_state = module_to_named_state(module, global_version=global_version)
    manifest = module_state.manifest
    if len(values) != manifest.total_elements:
        raise InvariantViolation("flat vector length does not match module state")
    flat_state = FlatState(
        global_version=global_version,
        values=values,
        manifest=manifest,
        checksum=sha256_json(
            flat_state_checksum_payload(
                global_version=global_version,
                values=values,
                manifest=manifest,
            )
        ),
    )
    validate_flat_state(flat_state)
    tensors: dict[str, np.ndarray] = {}
    flat_array = np.asarray(values, dtype=np.float64)
    for spec in manifest.tensors:
        chunk = flat_array[spec.offset : spec.offset + spec.length]
        tensors[spec.name] = chunk.astype(np.dtype(spec.dtype), copy=True).reshape(spec.shape)
    state = named_state_from_numpy(tensors, global_version=global_version)
    validate_named_state(state)
    return state
