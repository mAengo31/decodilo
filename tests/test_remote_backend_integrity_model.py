from decodilo.storage.remote_backend_integrity_model import (
    ArtifactIntegrityPolicy,
    IntegrityPolicy,
    ManifestIntegrityPolicy,
    evaluate_integrity_policy,
)


def test_integrity_policy_passes_by_default() -> None:
    assert evaluate_integrity_policy(IntegrityPolicy()).passed is True


def test_missing_content_hash_and_manifest_hash_fail() -> None:
    report = evaluate_integrity_policy(
        IntegrityPolicy(
            manifest=ManifestIntegrityPolicy(manifest_hash_required=False),
            artifact=ArtifactIntegrityPolicy(content_hash_required=False),
        )
    )

    assert report.passed is False
    assert "content hash validation is required" in report.errors
    assert "manifest hash validation is required" in report.errors


def test_missing_object_versioning_warns() -> None:
    report = evaluate_integrity_policy(
        IntegrityPolicy(
            artifact=ArtifactIntegrityPolicy(object_versioning_required=False)
        )
    )

    assert report.passed is True
    assert report.warnings
