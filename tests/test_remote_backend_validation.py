from decodilo.runtime.remote_backend_design_report import build_remote_backend_design_report
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_simulator import (
    RemoteBackendSimulatorConfig,
    run_remote_backend_simulation,
)


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="validation",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=7.168,
        peak_artifact_write_gbps=3.808,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=3.808,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_design_validation_detects_bandwidth_blocker() -> None:
    requirements = _requirements()
    simulation = run_remote_backend_simulation(
        requirements=requirements,
        config=RemoteBackendSimulatorConfig(
            read_gbps=1,
            write_gbps=1,
            ops_per_second=1000,
            conditional_put=True,
        ),
    )

    report = build_remote_backend_design_report(
        requirements=requirements,
        simulation=simulation,
    )

    assert report.recommendation.remote_backend_enabled is False
    assert report.recommendation.launch_allowed is False
    assert any("read_gbps" in blocker for blocker in report.blockers)


def test_design_validation_serializes() -> None:
    requirements = _requirements()
    simulation = run_remote_backend_simulation(
        requirements=requirements,
        config=RemoteBackendSimulatorConfig(
            read_gbps=10,
            write_gbps=5,
            ops_per_second=1000,
            conditional_put=True,
            consistency={"strong_read_after_write": True, "object_versioning": True},
        ),
    )

    report = build_remote_backend_design_report(
        requirements=requirements,
        simulation=simulation,
    )

    assert "no real remote artifact backend exists" in report.warnings
    assert report.recommendation.launch_ready is False
    assert report.model_validate_json(report.to_json()) == report

