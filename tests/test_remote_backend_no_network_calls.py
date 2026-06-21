import socket

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_simulator import (
    RemoteBackendSimulatorConfig,
    run_remote_backend_simulation,
)


def test_remote_backend_simulator_makes_no_network_calls(monkeypatch) -> None:
    def fail_socket(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("network call attempted")

    monkeypatch.setattr(socket, "socket", fail_socket)
    requirements = RemoteBackendRequirementSet(
        scenario_id="no-network",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=1,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )

    report = run_remote_backend_simulation(
        requirements=requirements,
        config=RemoteBackendSimulatorConfig(read_gbps=2, write_gbps=2, ops_per_second=10),
    )

    assert report.errors == []

