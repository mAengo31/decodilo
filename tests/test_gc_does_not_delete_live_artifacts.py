import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.gc import run_artifact_gc

pytestmark = [pytest.mark.unit, pytest.mark.storage]


def test_apply_gc_keeps_manifest_referenced_artifacts(tmp_path) -> None:
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    checkpoint = tmp_path / "syncer_checkpoint.json"
    for path in (run_spec, report, events, checkpoint):
        path.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-gc",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[checkpoint],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    run_artifact_gc(workdir=tmp_path, apply=True)

    assert checkpoint.exists()


def test_apply_gc_keeps_chunks_referenced_by_live_manifest(tmp_path) -> None:
    store = ChunkStore(tmp_path / "artifacts" / "store")
    manifest_path = tmp_path / "artifacts" / "global" / "state.artifact.json"
    manifest = store.write_bytes(
        artifact_id="run-gc:state",
        artifact_type="global_vector",
        run_id="run-gc",
        data=b"important state",
        chunk_size_bytes=4,
        manifest_path=manifest_path,
    )
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    artifact_manifest = build_artifact_manifest(
        run_id="run-gc",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[manifest_path],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", artifact_manifest)

    run_artifact_gc(workdir=tmp_path, apply=True)

    store.verify_manifest(manifest)
