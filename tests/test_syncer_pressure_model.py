import pytest

from decodilo.scaling.syncer_pressure_model import estimate_syncer_pressure


def test_syncer_pressure_increases_with_learners() -> None:
    few = estimate_syncer_pressure(
        learner_count=2,
        model_parameter_count=1000,
        bytes_per_parameter=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
    )
    many = estimate_syncer_pressure(
        learner_count=8,
        model_parameter_count=1000,
        bytes_per_parameter=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
    )

    assert many.syncer_merge_gbps_required > few.syncer_merge_gbps_required


def test_syncer_pressure_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        estimate_syncer_pressure(
            learner_count=0,
            model_parameter_count=1000,
            bytes_per_parameter=4,
            chunk_size_bytes=1024,
            sync_interval_steps=100,
            local_step_seconds=1,
        )

