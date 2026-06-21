import json
import shutil
import subprocess
import sys

import pytest

from decodilo.cli import _chunk_store_root_for_manifest
from decodilo.storage.artifact_reader import load_and_read_binary_artifact
from decodilo.storage.artifact_writer import ArtifactWriter, write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import ArtifactManifestError
from decodilo.storage.manifest import validate_artifact_manifest


def test_artifact_writer_reader_roundtrip_and_stable_manifest(tmp_path) -> None:
    store = ChunkStore(tmp_path)
    manifest_path = tmp_path / "manifests" / "artifact.json"
    writer = ArtifactWriter(
        store=store,
        artifact_id="artifact",
        artifact_type="test",
        run_id="run",
        chunk_size_bytes=4,
        metadata={"a": 1},
        manifest_path=manifest_path,
    )
    writer.write(b"abc")
    writer.write(b"defghi")
    manifest = writer.finish()

    assert load_and_read_binary_artifact(store=store, manifest_path=manifest_path) == b"abcdefghi"
    assert manifest.stable_json() == store.read_manifest(manifest_path).stable_json()


def test_manifest_hash_changes_when_metadata_or_chunks_change(tmp_path) -> None:
    store = ChunkStore(tmp_path)
    first = write_binary_artifact(
        store=store,
        data=b"data",
        artifact_id="artifact",
        artifact_type="test",
        run_id="run",
        metadata={"a": 1},
    )
    second = write_binary_artifact(
        store=store,
        data=b"data",
        artifact_id="artifact",
        artifact_type="test",
        run_id="run",
        metadata={"a": 2},
    )
    assert first.manifest_hash != second.manifest_hash


def test_atomic_failure_leaves_no_committed_manifest(tmp_path, monkeypatch) -> None:
    store = ChunkStore(tmp_path)
    manifest_path = tmp_path / "manifests" / "artifact.json"

    def fail_replace(src, dst):  # noqa: ANN001
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("decodilo.storage.chunk_store.os.replace", fail_replace)
    with pytest.raises(RuntimeError, match="simulated"):
        write_binary_artifact(
            store=store,
            data=b"data",
            artifact_id="artifact",
            artifact_type="test",
            run_id="run",
            manifest_path=manifest_path,
        )

    assert not manifest_path.exists()


def test_manifest_validation_rejects_tampering(tmp_path) -> None:
    store = ChunkStore(tmp_path)
    manifest = write_binary_artifact(
        store=store,
        data=b"data",
        artifact_id="artifact",
        artifact_type="test",
        run_id="run",
    )
    tampered = manifest.model_copy(update={"total_bytes": manifest.total_bytes + 1})
    with pytest.raises(ArtifactManifestError):
        validate_artifact_manifest(tampered)


def test_cli_manifest_root_detects_sibling_store(tmp_path) -> None:
    manifest_path = tmp_path / "checkpoint.artifact.json"
    (tmp_path / "store").mkdir()

    assert _chunk_store_root_for_manifest(manifest_path) == tmp_path / "store"


def test_cli_manifest_root_detects_live_artifact_chunks(tmp_path) -> None:
    manifest_path = tmp_path / "artifacts" / "learner-0" / "fragment.artifact.json"
    manifest_path.parent.mkdir(parents=True)
    (tmp_path / "chunks").mkdir()

    assert _chunk_store_root_for_manifest(manifest_path) == tmp_path / "chunks"


def test_cli_manifest_root_detects_live_artifact_store(tmp_path) -> None:
    manifest_path = tmp_path / "artifacts" / "learner-0" / "fragment.artifact.json"
    manifest_path.parent.mkdir(parents=True)
    (tmp_path / "artifacts" / "store").mkdir()

    assert _chunk_store_root_for_manifest(manifest_path) == tmp_path / "artifacts" / "store"


@pytest.mark.integration
def test_storage_cli_verifies_portable_manifest_layouts(tmp_path) -> None:
    store_root = tmp_path / "store-root"
    store = ChunkStore(store_root)
    manifest_path = store_root / "manifests" / "artifact.json"
    manifest = write_binary_artifact(
        store=store,
        data=b"portable payload",
        artifact_id="portable",
        artifact_type="test",
        run_id="run",
        chunk_size_bytes=4,
        manifest_path=manifest_path,
    )

    inferred = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "storage",
            "verify-artifact",
            str(manifest_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(inferred.stdout)["verified"] is True

    copied_manifest = tmp_path / "copied-manifest.json"
    shutil.copy2(manifest_path, copied_manifest)
    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "storage",
            "verify-artifact",
            str(copied_manifest),
            "--chunk-root",
            str(store_root),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(explicit.stdout)["root_hash"] == manifest.root_hash

    moved_root = tmp_path / "moved-root"
    shutil.copytree(store_root, moved_root)
    moved = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "storage",
            "verify-artifact",
            str(moved_root / "manifests" / "artifact.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert json.loads(moved.stdout)["storage_root"] == str(moved_root)

    inspect = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "storage",
            "inspect-artifact",
            str(moved_root / "manifests" / "artifact.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    inspected = json.loads(inspect.stdout)
    assert inspected["artifact_id"] == "portable"
    assert inspected["total_bytes"] == len(b"portable payload")
    assert inspected["chunk_count"] == len(manifest.chunk_hashes)
    assert inspected["root_hash"] == manifest.root_hash
    assert inspected["manifest_hash"] == manifest.manifest_hash
    assert inspected["storage_root"] == str(moved_root)

    lonely_manifest = tmp_path / "lonely" / "manifests" / "artifact.json"
    lonely_manifest.parent.mkdir(parents=True)
    shutil.copy2(manifest_path, lonely_manifest)
    missing = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "storage",
            "verify-artifact",
            str(lonely_manifest),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert missing.returncode != 0
    assert "missing chunk" in missing.stderr
