from decodilo.scaling.bandwidth import estimate_outer_loop_bandwidth
from decodilo.scaling.checkpointing import estimate_checkpointing


def test_bandwidth_estimator_positive_and_compression_reduces_bandwidth() -> None:
    base = estimate_outer_loop_bandwidth(
        parameter_count=1_000_000,
        bytes_per_parameter=4,
        num_learners=4,
        num_fragments=8,
        sync_interval_steps=100,
        local_step_seconds=1.0,
    )
    compressed = estimate_outer_loop_bandwidth(
        parameter_count=1_000_000,
        bytes_per_parameter=4,
        num_learners=4,
        num_fragments=8,
        sync_interval_steps=100,
        local_step_seconds=1.0,
        compression_bits=8,
    )

    assert base.bytes_per_full_model > 0
    assert base.average_bandwidth_gbps > 0
    assert compressed.average_bandwidth_gbps < base.average_bandwidth_gbps


def test_more_learners_increases_and_longer_interval_reduces_average_bandwidth() -> None:
    small = estimate_outer_loop_bandwidth(
        parameter_count=1_000_000,
        bytes_per_parameter=2,
        num_learners=2,
        num_fragments=8,
        sync_interval_steps=100,
        local_step_seconds=1.0,
    )
    more_learners = estimate_outer_loop_bandwidth(
        parameter_count=1_000_000,
        bytes_per_parameter=2,
        num_learners=4,
        num_fragments=8,
        sync_interval_steps=100,
        local_step_seconds=1.0,
    )
    longer_interval = estimate_outer_loop_bandwidth(
        parameter_count=1_000_000,
        bytes_per_parameter=2,
        num_learners=2,
        num_fragments=8,
        sync_interval_steps=200,
        local_step_seconds=1.0,
    )

    assert more_learners.aggregate_bytes_per_sync_round > small.aggregate_bytes_per_sync_round
    assert longer_interval.average_bandwidth_gbps < small.average_bandwidth_gbps


def test_checkpoint_retention_increases_storage() -> None:
    one = estimate_checkpointing(
        parameter_count=1_000,
        bytes_per_parameter=2,
        optimizer_multiplier=2,
        num_learners=2,
        checkpoint_interval_minutes=10,
        retention_count=1,
    )
    three = estimate_checkpointing(
        parameter_count=1_000,
        bytes_per_parameter=2,
        optimizer_multiplier=2,
        num_learners=2,
        checkpoint_interval_minutes=10,
        retention_count=3,
    )

    assert three.total_retained_checkpoint_bytes == one.total_retained_checkpoint_bytes * 3
