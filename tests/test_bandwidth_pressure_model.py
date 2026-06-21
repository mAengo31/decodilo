from decodilo.scaling.bandwidth_pressure_model import estimate_bandwidth_pressure


def test_compression_reduces_bandwidth_pressure() -> None:
    uncompressed = estimate_bandwidth_pressure(
        learner_count=8,
        model_parameter_count=1000,
        bytes_per_parameter=4,
        fragment_count=4,
        sync_interval_steps=10,
        local_step_seconds=1,
    )
    compressed = estimate_bandwidth_pressure(
        learner_count=8,
        model_parameter_count=1000,
        bytes_per_parameter=4,
        fragment_count=4,
        sync_interval_steps=10,
        local_step_seconds=1,
        compression_bits=8,
    )

    assert compressed.average_bandwidth_gbps < uncompressed.average_bandwidth_gbps


def test_bandwidth_saturation_warning_triggers() -> None:
    estimate = estimate_bandwidth_pressure(
        learner_count=8,
        model_parameter_count=1_000_000,
        bytes_per_parameter=4,
        fragment_count=4,
        sync_interval_steps=1,
        local_step_seconds=1,
        bandwidth_cap_gbps=0.001,
    )

    assert estimate.bandwidth_saturation_ratio > 1
    assert any("cap exceeded" in warning for warning in estimate.warnings)

