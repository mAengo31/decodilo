import pytest

from decodilo.storage.checksums import sha256_file
from decodilo.syncer.recovery_audit import validate_recovery_manifest_chain
from decodilo.syncer.recovery_manifest import (
    make_recovery_manifest,
    write_recovery_manifest_atomic,
)

pytestmark = [pytest.mark.lifecycle, pytest.mark.replay]


def _write_manifest(tmp_path, version: int, previous_hash: str | None = None):
    checkpoint = tmp_path / f"checkpoint-{version}.json"
    checkpoint.write_text(f'{{"version": {version}}}\n', encoding="utf-8")
    manifest = make_recovery_manifest(
        run_id="run-chain",
        manifest_id=f"recovery-{version}",
        created_logical_time=version,
        global_version=version,
        checkpoint_ref={"path": str(checkpoint)},
        checkpoint_storage_mode="inline",
        recovery_source="inline",
        required_artifact_hashes={str(checkpoint): sha256_file(checkpoint)},
        previous_recovery_manifest_hash=previous_hash,
    )
    path = tmp_path / "recovery_manifests" / f"recovery-{version}.json"
    write_recovery_manifest_atomic(path, manifest)
    write_recovery_manifest_atomic(tmp_path / "recovery_manifest.json", manifest)
    return manifest


def test_valid_recovery_manifest_chain_passes(tmp_path) -> None:
    first = _write_manifest(tmp_path, 1)
    _write_manifest(tmp_path, 2, previous_hash=first.manifest_hash)

    report = validate_recovery_manifest_chain(tmp_path)

    assert report.passed is True
    assert report.manifests_checked == 2


def test_missing_previous_recovery_manifest_fails(tmp_path) -> None:
    _write_manifest(tmp_path, 2, previous_hash="missing-hash")

    report = validate_recovery_manifest_chain(tmp_path)

    assert report.passed is False
    assert any("missing previous" in error for error in report.errors)


def test_global_version_regression_fails(tmp_path) -> None:
    previous = _write_manifest(tmp_path, 5)
    _write_manifest(tmp_path, 4, previous_hash=previous.manifest_hash)

    report = validate_recovery_manifest_chain(tmp_path)

    assert report.passed is False
    assert any("global_version regression" in error for error in report.errors)

