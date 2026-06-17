import numpy as np

from decodilo.storage.tensor_codec import decode_tensors, encode_tensors
from decodilo.trainer.named_state import named_state_from_numpy, tensor_array, validate_named_state


def test_binary_named_state_roundtrip_preserves_order_dtype_shape_and_checksum() -> None:
    state = named_state_from_numpy(
        {
            "z.bias": np.asarray([1, 2, 3], dtype=np.int32),
            "a.weight": np.asarray([[1.5, 2.5]], dtype=np.float32),
        },
        global_version=7,
    )
    validate_named_state(state)

    encoded = encode_tensors(
        {spec.name: tensor_array(state, spec.name) for spec in state.manifest.tensors},
        chunk_size_bytes=8,
        created_by="test",
    )
    decoded = decode_tensors(encoded.data, encoded.metadata)

    assert [spec.name for spec in encoded.metadata.tensors] == ["a.weight", "z.bias"]
    np.testing.assert_array_equal(decoded["a.weight"], tensor_array(state, "a.weight"))
    np.testing.assert_array_equal(decoded["z.bias"], tensor_array(state, "z.bias"))


def test_binary_codec_canonicalizes_big_endian_numeric_arrays() -> None:
    source = np.asarray([1.0, 2.0, 3.0], dtype=">f4")

    encoded = encode_tensors({"weights": source}, chunk_size_bytes=8, created_by="test")
    decoded = decode_tensors(encoded.data, encoded.metadata)

    assert encoded.metadata.tensors[0].dtype == "float32"
    assert encoded.metadata.tensors[0].byte_order == "little"
    np.testing.assert_array_equal(decoded["weights"], source.astype(np.float32))
