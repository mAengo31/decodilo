import pytest

from decodilo.storage.checksums import sha256_file
from decodilo.syncer.recovery_manifest import (
    load_recovery_manifest,
    make_recovery_manifest,
    validate_recovery_manifest,
    write_recovery_manifest_atomic,
)

pytestmark = pytest.mark.unit


def test_recovery_manifest_written_and_validates(tmp_path) -> None:
    checkpoint = tmp_path / "syncer_checkpoint.json"
    checkpoint.write_text('{"ok": true}\n', encoding="utf-8")
    manifest = make_recovery_manifest(
        run_id="run-recovery",
        manifest_id="recovery-1",
        created_logical_time=1,
        checkpoint_ref={"path": str(checkpoint)},
        checkpoint_storage_mode="inline",
        recovery_source="inline",
        required_artifact_hashes={str(checkpoint): sha256_file(checkpoint)},
    )
    write_recovery_manifest_atomic(tmp_path / "recovery_manifest.json", manifest)

    loaded = load_recovery_manifest(tmp_path / "recovery_manifest.json")

    assert loaded.manifest_hash == manifest.manifest_hash


def test_missing_required_artifact_fails_recovery_manifest_validation(tmp_path) -> None:
    manifest = make_recovery_manifest(
        run_id="run-recovery",
        manifest_id="recovery-1",
        created_logical_time=1,
        checkpoint_ref={"path": str(tmp_path / "missing.json")},
        checkpoint_storage_mode="inline",
        recovery_source="inline",
    )

    with pytest.raises(Exception, match="missing recovery checkpoint"):
        validate_recovery_manifest(manifest)

