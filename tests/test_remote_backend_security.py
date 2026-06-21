import pytest

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_security import (
    RemoteBackendSecurityChecklist,
    evaluate_remote_backend_security,
)


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="security",
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


def test_security_check_fails_without_auth_or_hash_validation() -> None:
    report = evaluate_remote_backend_security(
        requirements=_requirements(),
        checklist=RemoteBackendSecurityChecklist(
            auth_required=False,
            client_side_hash_validation=False,
        ),
    )

    assert report.passed is False
    assert any("authentication" in error for error in report.errors)
    assert any("hash" in error for error in report.errors)


def test_security_check_warns_without_versioning() -> None:
    report = evaluate_remote_backend_security(
        requirements=_requirements(),
        checklist=RemoteBackendSecurityChecklist(object_versioning=False),
    )

    assert report.passed is True
    assert any("versioning" in warning for warning in report.warnings)


def test_security_check_rejects_secret_values() -> None:
    with pytest.raises(ValueError):
        RemoteBackendSecurityChecklist(credential_names=["TOKEN=secret-value"])

