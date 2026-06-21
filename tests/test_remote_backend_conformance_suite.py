from decodilo.storage.remote_backend_conformance import (
    load_remote_backend_conformance_report,
    passing_simulator_config,
    run_disabled_backend_conformance,
    run_remote_backend_conformance_suite,
    write_remote_backend_conformance_report,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m016-conformance",
        target_learner_count=4,
        stress_learner_count=8,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=10,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_passing_simulator_passes_conformance(tmp_path) -> None:
    requirements = _requirements()
    report = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )

    assert report.passed is True
    assert report.conformance_status == "passed"
    assert report.remote_backend_enabled is False
    assert report.launch_allowed is False

    path = tmp_path / "conformance.json"
    write_remote_backend_conformance_report(path, report)
    assert load_remote_backend_conformance_report(path) == report


def test_disabled_backend_reports_disabled_not_usable() -> None:
    report = run_disabled_backend_conformance()

    assert report.disabled_backend is True
    assert report.passed is False
    assert report.conformance_status == "disabled"
