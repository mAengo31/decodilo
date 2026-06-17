import json

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.storage.artifact_reference_audit import audit_artifact_references
from decodilo.storage.chunk_store import ChunkStore

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def _base(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    return run_spec, report, events


def test_valid_run_audit_passes(tmp_path) -> None:
    run_spec, report, events = _base(tmp_path)
    manifest = build_artifact_manifest(
        run_id="run-audit",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    audit = audit_artifact_references(tmp_path)

    assert audit.passed is True


def test_untracked_artifact_manifest_fails_audit(tmp_path) -> None:
    run_spec, report, events = _base(tmp_path)
    store = ChunkStore(tmp_path / "artifacts" / "store")
    store.write_bytes(
        artifact_id="run-audit:state",
        artifact_type="global_vector",
        run_id="run-audit",
        data=b"payload",
        manifest_path=tmp_path / "artifacts" / "global" / "state.artifact.json",
    )
    manifest = build_artifact_manifest(
        run_id="run-audit",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    audit = audit_artifact_references(tmp_path)

    assert audit.passed is False
    assert audit.untracked_artifacts


def test_event_log_artifact_ref_missing_from_manifest_fails_audit(tmp_path) -> None:
    run_spec, report, events = _base(tmp_path)
    ref_path = tmp_path / "artifacts" / "global" / "missing.artifact.json"
    events.write_text(
        json.dumps({"payload": {"artifact_ref": {"manifest_path": str(ref_path)}}}) + "\n",
        encoding="utf-8",
    )
    manifest = build_artifact_manifest(
        run_id="run-audit",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    audit = audit_artifact_references(tmp_path)

    assert str(ref_path) in audit.missing_references


def test_checksum_mismatch_fails_audit(tmp_path) -> None:
    run_spec, report, events = _base(tmp_path)
    manifest = build_artifact_manifest(
        run_id="run-audit",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)
    run_spec.write_text('{"tampered":true}\n', encoding="utf-8")

    audit = audit_artifact_references(tmp_path)

    assert audit.passed is False
    assert str(run_spec) in audit.checksum_errors


def test_outside_workdir_reference_fails_audit(tmp_path) -> None:
    run_spec, report, events = _base(tmp_path)
    outside = tmp_path.parent / "outside-artifact.json"
    outside.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-audit",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=events,
        syncer_checkpoint_paths=[outside],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    audit = audit_artifact_references(tmp_path)

    assert audit.passed is False
    assert str(outside) in audit.outside_workdir_errors
