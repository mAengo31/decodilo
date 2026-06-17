from itertools import islice

from decodilo.trainer.synthetic_large_state import SyntheticLargeStateSource


def test_logical_1gb_state_materializes_only_sampled_chunks() -> None:
    source = SyntheticLargeStateSource(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        logical_parameter_count=512 * 1024 * 1024,
        bytes_per_parameter=2,
    )

    _sample = list(islice(source.iter_fragments(max_fragment_bytes=4096), 2))

    assert source.total_logical_bytes == 1024 * 1024 * 1024
    assert source.bytes_materialized == 8192
    assert source.bytes_materialized < source.total_logical_bytes
