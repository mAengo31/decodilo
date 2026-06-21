from decodilo.storage.remote_backend_contract import (
    RemoteArtifactBackendCapabilities,
    validate_remote_backend_contract,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="contract",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=7,
        peak_artifact_write_gbps=4,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=4,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_contract_report_identifies_missing_capabilities() -> None:
    report = validate_remote_backend_contract(
        capabilities=RemoteArtifactBackendCapabilities(backend_name="future"),
        requirements=_requirements(),
    )

    assert report.passed is False
    assert "supports_conditional_put" in report.missing_capabilities
    assert report.remote_backend_enabled is False


def test_capabilities_serialize() -> None:
    caps = RemoteArtifactBackendCapabilities(
        backend_name="sim",
        supports_range_read=True,
    )

    assert caps.model_dump(mode="json")["supports_range_read"] is True

