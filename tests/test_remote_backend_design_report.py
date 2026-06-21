from decodilo.runtime.remote_backend_design_report import (
    RemoteBackendDesignValidationReport,
    build_remote_backend_design_report,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_simulator import (
    RemoteBackendSimulatorConfig,
    run_remote_backend_simulation,
)


def test_remote_backend_design_report_shape() -> None:
    requirements = RemoteBackendRequirementSet(
        scenario_id="design",
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
    simulation = run_remote_backend_simulation(
        requirements=requirements,
        config=RemoteBackendSimulatorConfig(read_gbps=2, write_gbps=2, ops_per_second=10),
    )

    report = build_remote_backend_design_report(
        requirements=requirements,
        simulation=simulation,
    )

    assert isinstance(report, RemoteBackendDesignValidationReport)
    assert report.report_schema_version == 1
    assert report.recommendation.remote_backend_enabled is False
    assert report.recommendation.launch_allowed is False

