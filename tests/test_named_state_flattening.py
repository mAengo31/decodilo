import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import (
    flatten_named_state,
    reconstruct_named_state,
    validate_flat_state,
)
from decodilo.trainer.named_state import named_state_from_numpy, tensor_array, validate_named_state


def test_named_state_flatten_reconstruct_roundtrip_preserves_dtype_shape() -> None:
    state = named_state_from_numpy(
        {
            "b": np.arange(3, dtype=np.float32),
            "a": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64),
        },
        global_version=3,
    )

    flat = flatten_named_state(state)
    reconstructed = reconstruct_named_state(flat)

    assert [spec.name for spec in state.manifest.tensors] == ["a", "b"]
    np.testing.assert_array_equal(tensor_array(reconstructed, "a"), tensor_array(state, "a"))
    np.testing.assert_array_equal(tensor_array(reconstructed, "b"), tensor_array(state, "b"))
    assert reconstructed.manifest.tensors[0].dtype == "float64"
    assert reconstructed.manifest.tensors[1].dtype == "float32"
    assert reconstructed.checksum == state.checksum


def test_tensor_order_is_deterministic_independent_of_insertion_order() -> None:
    tensors_a = {"z": np.array([1.0]), "a": np.array([2.0, 3.0])}
    tensors_b = {"a": np.array([2.0, 3.0]), "z": np.array([1.0])}

    state_a = named_state_from_numpy(tensors_a, global_version=1)
    state_b = named_state_from_numpy(tensors_b, global_version=1)

    assert flatten_named_state(state_a).checksum == flatten_named_state(state_b).checksum
    assert state_a.checksum == state_b.checksum


def test_corrupted_tensor_and_flat_state_checksums_are_rejected() -> None:
    state = named_state_from_numpy({"weights": np.array([1.0, 2.0])}, global_version=0)
    corrupted_spec = state.manifest.tensors[0].model_copy(update={"checksum": "bad"})
    corrupted_manifest = state.manifest.model_copy(update={"tensors": [corrupted_spec]})
    corrupted_state = state.model_copy(update={"manifest": corrupted_manifest})

    with pytest.raises(InvariantViolation):
        validate_named_state(corrupted_state)

    flat = flatten_named_state(state)
    bad_flat = flat.model_copy(update={"values": [999.0, 2.0]})
    with pytest.raises(InvariantViolation):
        validate_flat_state(bad_flat)


def test_identical_and_different_states_have_expected_checksums() -> None:
    first = named_state_from_numpy({"weights": np.array([1.0, 2.0])}, global_version=0)
    second = named_state_from_numpy({"weights": np.array([1.0, 2.0])}, global_version=0)
    third = named_state_from_numpy({"weights": np.array([1.0, 3.0])}, global_version=0)

    assert first.checksum == second.checksum
    assert first.checksum != third.checksum
