from itertools import islice

from decodilo.trainer.synthetic_large_state import (
    SyntheticLargeStateSource,
    verify_synthetic_chunk,
)


def test_synthetic_large_state_iterates_without_full_allocation() -> None:
    source = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        logical_parameter_count=512 * 1024 * 1024,
        bytes_per_parameter=2,
    )

    chunks = list(islice(source.iter_fragments(max_fragment_bytes=1024), 3))

    assert source.total_logical_bytes == 1024 * 1024 * 1024
    assert len(chunks) == 3
    assert source.bytes_materialized == 3 * 1024
    assert chunks[0].logical_offset_bytes == 0
    assert chunks[1].logical_offset_bytes == 1024
    verify_synthetic_chunk(chunks[0])


def test_synthetic_large_state_hashes_are_seeded_and_deterministic() -> None:
    first = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=1,
        logical_parameter_count=1024,
    )
    second = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=1,
        logical_parameter_count=1024,
    )
    different = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=2,
        logical_parameter_count=1024,
    )

    assert next(first.iter_fragments(max_fragment_bytes=128)).checksum == next(
        second.iter_fragments(max_fragment_bytes=128)
    ).checksum
    assert next(first.iter_fragments(max_fragment_bytes=128)).checksum != next(
        different.iter_fragments(max_fragment_bytes=128)
    ).checksum
