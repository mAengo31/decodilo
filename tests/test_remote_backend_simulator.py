import pytest

from decodilo.storage.remote_backend_consistency import RemoteBackendConsistencyConfig
from decodilo.storage.remote_backend_simulator import (
    LocalRemoteBackendSimulator,
    RemoteBackendSimulatorConfig,
)


def test_strong_read_after_write_visible_immediately() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(read_gbps=10, write_gbps=10, ops_per_second=100)
    )

    sim.put_artifact("a", b"hello")

    assert sim.get_artifact("a") == b"hello"
    assert "a" in sim.list_artifacts()


def test_eventual_consistency_delays_get() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=10,
            ops_per_second=100,
            consistency=RemoteBackendConsistencyConfig(
                strong_read_after_write=False,
                visibility_delay_ticks=5,
            ),
        )
    )

    sim.put_artifact("a", b"hello")
    with pytest.raises(KeyError):
        sim.get_artifact("a")
    sim.advance_logical_time(10)
    assert sim.get_artifact("a") == b"hello"


def test_conditional_put_prevents_overwrite() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(read_gbps=10, write_gbps=10, ops_per_second=100)
    )
    sim.put_artifact("a", b"hello")

    with pytest.raises(ValueError, match="conditional"):
        sim.put_artifact("a", b"new", expected_version=999)

