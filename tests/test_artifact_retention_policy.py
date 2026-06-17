import pytest

from decodilo.storage.lifecycle_policy import ArtifactRetentionPolicy

pytestmark = [pytest.mark.unit, pytest.mark.storage]


def test_retention_policy_defaults_to_dry_run() -> None:
    policy = ArtifactRetentionPolicy()

    assert policy.dry_run is True
    assert policy.keep_latest_checkpoints == 1
    assert policy.delete_temporary_artifacts is True

