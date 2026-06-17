import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import (
    assemble_flat_fragments,
    flatten_named_state,
    fragment_flat_state,
    make_fragment_layout,
    reconstruct_named_state,
    validate_flat_fragment,
)
from decodilo.trainer.named_state import named_state_from_numpy, tensor_array


def test_flat_fragments_round_trip_to_named_state() -> None:
    state = named_state_from_numpy(
        {"a": np.arange(4, dtype=np.float32), "b": np.arange(6, dtype=np.float64).reshape(2, 3)},
        global_version=2,
    )
    flat = flatten_named_state(state)
    layout = make_fragment_layout(total_elements=len(flat.values), num_fragments=3)
    fragments = fragment_flat_state(flat, layout)

    assembled = assemble_flat_fragments(
        fragments=fragments,
        manifest=flat.manifest,
        global_version=flat.global_version,
    )
    reconstructed = reconstruct_named_state(assembled)

    np.testing.assert_array_equal(tensor_array(reconstructed, "a"), tensor_array(state, "a"))
    np.testing.assert_array_equal(tensor_array(reconstructed, "b"), tensor_array(state, "b"))


def test_corrupted_flat_fragment_checksum_is_rejected() -> None:
    state = named_state_from_numpy({"weights": np.array([1.0, 2.0])}, global_version=0)
    flat = flatten_named_state(state)
    fragment = fragment_flat_state(
        flat,
        make_fragment_layout(total_elements=len(flat.values), num_fragments=1),
    )[0]
    corrupted = fragment.model_copy(update={"data": [9.0, 2.0]})

    with pytest.raises(InvariantViolation):
        validate_flat_fragment(corrupted)
