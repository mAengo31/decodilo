import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import (
    ArtifactTransportPolicy,
    LocalArtifactTransport,
)
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore


def _write_ref(tmp_path):
    transport = LocalArtifactTransport(
        policy=ArtifactTransportPolicy(
            workdir=str(tmp_path),
            artifact_root=str(tmp_path / "artifacts"),
        )
    )
    store = ChunkStore(tmp_path / "chunks")
    manifest_path = tmp_path / "artifacts" / "payload.artifact.json"
    manifest = write_binary_artifact(
        store=store,
        data=b"payload",
        artifact_id="artifact",
        artifact_type="test",
        run_id="run",
        manifest_path=manifest_path,
    )
    return transport, transport.make_ref(
        manifest=manifest,
        manifest_path=manifest_path,
        chunk_root=tmp_path / "chunks",
        created_by="test",
    )


def test_local_artifact_ref_round_trips_and_serializes_stably(tmp_path) -> None:
    transport, ref = _write_ref(tmp_path)

    assert transport.read_bytes(ref) == b"payload"
    assert ref.stable_json() == ref.stable_json()


def test_artifact_ref_rejects_path_traversal_and_outside_workdir(tmp_path) -> None:
    transport, ref = _write_ref(tmp_path)

    with pytest.raises(InvariantViolation, match="escapes"):
        transport.validate_ref(ref.model_copy(update={"manifest_path": "../outside.json"}))

    outside = tmp_path.parent / "outside-artifact.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(InvariantViolation):
        transport.make_ref(
            manifest=transport.validate_ref(ref),
            manifest_path=outside,
            chunk_root=tmp_path / "chunks",
            created_by="test",
        )


def test_artifact_ref_rejects_corruption_and_symlink_escape(tmp_path) -> None:
    transport, ref = _write_ref(tmp_path)

    with pytest.raises(InvariantViolation, match="manifest_hash"):
        transport.validate_ref(ref.model_copy(update={"manifest_hash": "0" * 64}))

    outside_manifest = tmp_path.parent / "escape-artifact.json"
    outside_manifest.write_text("{}", encoding="utf-8")
    symlink = tmp_path / "artifacts" / "escape-link.json"
    symlink.symlink_to(outside_manifest)
    with pytest.raises(InvariantViolation, match="escapes"):
        transport.validate_ref(
            ref.model_copy(update={"manifest_path": "artifacts/escape-link.json"})
        )
