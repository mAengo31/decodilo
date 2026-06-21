from decodilo.scaling.artifact_pressure_model import estimate_artifact_pressure


def test_more_learners_increases_artifact_pressure() -> None:
    base = estimate_artifact_pressure(
        learner_count=2,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
    )
    more = estimate_artifact_pressure(
        learner_count=4,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
    )

    assert more.artifact_write_gbps_required > base.artifact_write_gbps_required


def test_smaller_chunks_increase_artifact_ops() -> None:
    small = estimate_artifact_pressure(
        learner_count=4,
        model_parameter_count=10_000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
    )
    large = estimate_artifact_pressure(
        learner_count=4,
        model_parameter_count=10_000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=8192,
        sync_interval_steps=100,
        local_step_seconds=1,
    )

    assert small.artifact_ops_per_second > large.artifact_ops_per_second

