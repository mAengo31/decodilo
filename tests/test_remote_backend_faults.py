import pytest

from decodilo.storage.remote_backend_faults import RemoteBackendFaultConfig
from decodilo.storage.remote_backend_simulator import (
    LocalRemoteBackendSimulator,
    RemoteBackendSimulatorConfig,
)


def test_transient_failures_are_retryable_and_counted() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=10,
            ops_per_second=100,
            faults=RemoteBackendFaultConfig(transient_put_failures=1),
        )
    )

    with pytest.raises(RuntimeError, match="transient"):
        sim.put_artifact("a", b"data")
    sim.put_artifact("a", b"data")

    assert sim.metrics.simulated_retries == 1


def test_corrupt_read_is_detected() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=10,
            ops_per_second=100,
            faults=RemoteBackendFaultConfig(corrupt_read_after=1),
        )
    )
    sim.put_artifact("a", b"data")

    with pytest.raises(ValueError, match="corrupt"):
        sim.get_artifact("a")
    assert sim.metrics.simulated_corruptions_detected == 1


def test_throttling_metrics_trigger_when_caps_exceeded() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(read_gbps=0.001, write_gbps=0.001, ops_per_second=100)
    )

    sim.put_artifact("a", b"x" * 2_000_000)
    sim.get_artifact("a")

    assert sim.metrics.simulated_write_throttle_events > 0
    assert sim.metrics.simulated_read_throttle_events > 0

