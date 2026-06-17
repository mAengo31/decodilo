import json

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.storage.gc import plan_artifact_gc, run_artifact_gc

pytestmark = [pytest.mark.unit, pytest.mark.storage]


def _write_minimal_run(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    run_spec.write_text('{"run_id":"run-gc"}\n', encoding="utf-8")
    report.write_text(
        '{"run_id":"run-gc","metrics":{},"final_global_version":0}\n',
        encoding="utf-8",
    )
    events.write_text("", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-gc",
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


def test_gc_plan_marks_orphan_temporary_artifact(tmp_path) -> None:
    _write_minimal_run(tmp_path)
    temp = tmp_path / "partial.tmp"
    temp.write_text("delete me\n", encoding="utf-8")

    plan = plan_artifact_gc(workdir=tmp_path)

    assert str(temp) in plan.delete_candidates
    assert plan.bytes_reclaimable >= temp.stat().st_size


def test_dry_run_deletes_nothing_and_apply_deletes_only_orphan(tmp_path) -> None:
    _write_minimal_run(tmp_path)
    temp = tmp_path / "partial.tmp"
    temp.write_text("delete me\n", encoding="utf-8")

    dry = run_artifact_gc(workdir=tmp_path, apply=False)
    applied = run_artifact_gc(workdir=tmp_path, apply=True)

    assert dry.artifacts_deleted == 0
    assert applied.artifacts_deleted == 1
    assert not temp.exists()
    assert (tmp_path / "run_spec.json").exists()


def test_gc_report_schema_serializes(tmp_path) -> None:
    _write_minimal_run(tmp_path)

    report = run_artifact_gc(workdir=tmp_path, apply=False)
    payload = json.loads(report.model_dump_json())

    assert payload["dry_run"] is True
