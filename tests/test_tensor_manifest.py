import numpy as np
import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.flattening import (
    flatten_named_state,
    make_fragment_layout,
    validate_fragment_layout,
)
from decodilo.trainer.named_state import named_state_from_numpy
from decodilo.trainer.tensor_manifest import validate_manifest


def test_manifest_offsets_cover_full_state_without_gaps() -> None:
    state = named_state_from_numpy(
        {"a": np.ones((2, 2), dtype=np.float32), "b": np.ones(3, dtype=np.float32)},
        global_version=0,
    )

    validate_manifest(state.manifest)
    specs = state.manifest.tensors
    assert specs[0].offset == 0
    assert specs[0].length == 4
    assert specs[1].offset == 4
    assert state.manifest.total_elements == 7


def test_fragment_layout_has_no_empty_fragments_when_requested_count_exceeds_elements() -> None:
    flat = flatten_named_state(
        named_state_from_numpy({"weights": np.array([1.0, 2.0, 3.0])}, global_version=0)
    )
    layout = make_fragment_layout(total_elements=len(flat.values), num_fragments=10)

    validate_fragment_layout(layout)
    assert len(layout.spans) == 3
    assert all(span["length"] > 0 for span in layout.spans)


def test_fragment_layout_checksum_detects_tampering() -> None:
    layout = make_fragment_layout(total_elements=5, num_fragments=2)
    tampered = layout.model_copy(update={"spans": [{"fragment_id": 0, "offset": 0, "length": 5}]})

    with pytest.raises(InvariantViolation):
        validate_fragment_layout(tampered)
