from decodilo.storage.remote_backend_consistency import RemoteBackendConsistencyConfig
from decodilo.storage.remote_backend_simulator import (
    LocalRemoteBackendSimulator,
    RemoteBackendSimulatorConfig,
)


def test_stale_list_results_follow_logical_time() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=10,
            ops_per_second=100,
            consistency=RemoteBackendConsistencyConfig(stale_list_ticks=5),
        )
    )

    sim.put_artifact("a", b"data")
    assert "a" not in sim.list_artifacts()
    sim.advance_logical_time(10)
    assert "a" in sim.list_artifacts()


def test_delete_lifecycle_uses_logical_time() -> None:
    sim = LocalRemoteBackendSimulator(
        RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=10,
            ops_per_second=100,
            consistency=RemoteBackendConsistencyConfig(visibility_delay_ticks=3),
        )
    )
    sim.put_artifact("a", b"data")
    sim.delete_artifact("a")
    sim.advance_logical_time(4)

    assert "a" not in sim.list_artifacts()

