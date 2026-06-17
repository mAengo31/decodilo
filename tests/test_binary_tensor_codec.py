import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.storage.tensor_binary_format import TensorBinaryMetadata, TensorBinarySpec
from decodilo.storage.tensor_codec import decode_tensors, encode_tensors


def test_numpy_tensors_roundtrip_deterministically() -> None:
    tensors = {
        "z": np.asarray([[1, 2], [3, 4]], dtype=np.int32),
        "a": np.asarray([1.5, 2.5], dtype=np.float32),
    }

    first = encode_tensors(tensors, chunk_size_bytes=8, created_by="test")
    second = encode_tensors(
        {"a": tensors["a"], "z": tensors["z"]},
        chunk_size_bytes=8,
        created_by="test",
    )
    decoded = decode_tensors(first.data, first.metadata)

    assert first.data == second.data
    assert first.metadata.metadata_hash() == second.metadata.metadata_hash()
    np.testing.assert_array_equal(decoded["a"], tensors["a"])
    np.testing.assert_array_equal(decoded["z"], tensors["z"])
    assert [spec.name for spec in first.metadata.tensors] == ["a", "z"]


def test_non_contiguous_input_is_canonicalized() -> None:
    source = np.arange(12, dtype=np.float64).reshape(3, 4).T
    assert not source.flags.c_contiguous

    encoded = encode_tensors({"weights": source}, chunk_size_bytes=16, created_by="test")
    decoded = decode_tensors(encoded.data, encoded.metadata)

    np.testing.assert_array_equal(decoded["weights"], source)
    assert decoded["weights"].flags.c_contiguous


def test_unsupported_object_dtype_and_nonfinite_rejected() -> None:
    with pytest.raises(InvariantViolation, match="object dtype"):
        encode_tensors({"bad": np.asarray([object()])}, chunk_size_bytes=16, created_by="test")

    with pytest.raises(InvariantViolation, match="non-finite"):
        encode_tensors(
            {"bad": np.asarray([np.nan], dtype=np.float32)},
            chunk_size_bytes=16,
            created_by="test",
        )


def test_tensor_checksum_and_byte_length_mismatch_rejected() -> None:
    encoded = encode_tensors(
        {"weights": np.asarray([1.0, 2.0], dtype=np.float64)},
        chunk_size_bytes=8,
        created_by="test",
    )
    corrupted = bytearray(encoded.data)
    corrupted[0] ^= 1

    with pytest.raises(InvariantViolation, match="checksum"):
        decode_tensors(bytes(corrupted), encoded.metadata)

    spec = encoded.metadata.tensors[0].model_copy(update={"byte_length": 999})
    metadata = encoded.metadata.model_copy(update={"tensors": [spec]})
    with pytest.raises(InvariantViolation, match="byte"):
        decode_tensors(encoded.data, metadata)


def test_duplicate_tensor_names_and_absurd_shape_rejected() -> None:
    spec = TensorBinarySpec(
        name="x",
        dtype="float32",
        shape=[1],
        num_elements=1,
        byte_order="little",
        byte_offset=0,
        byte_length=4,
        chunk_start=0,
        chunk_end=1,
        tensor_checksum="0" * 64,
    )
    with pytest.raises(ValueError, match="duplicate"):
        TensorBinaryMetadata(created_by="test", tensors=[spec, spec])

    overlap = spec.model_copy(
        update={
            "name": "y",
            "byte_offset": 0,
            "byte_length": 4,
        }
    )
    with pytest.raises(ValueError, match="contiguous"):
        TensorBinaryMetadata(created_by="test", tensors=[spec, overlap])

    with pytest.raises(ValueError, match="too large"):
        TensorBinarySpec(
            name="huge",
            dtype="float32",
            shape=[2**62, 4],
            num_elements=2**64,
            byte_order="little",
            byte_offset=0,
            byte_length=4,
            chunk_start=0,
            chunk_end=1,
            tensor_checksum="0" * 64,
        )
