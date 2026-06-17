import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.storage.gc import plan_artifact_gc, run_artifact_gc

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def _minimal_run(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-tx",
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


def test_gc_apply_writes_transaction_log_and_stages_delete(tmp_path) -> None:
    _minimal_run(tmp_path)
    victim = tmp_path / "victim.tmp"
    victim.write_text("delete\n", encoding="utf-8")

    report = run_artifact_gc(workdir=tmp_path, apply=True)

    assert report.transaction_id
    assert report.transaction_state == "completed"
    assert report.artifacts_deleted == 1
    assert not victim.exists()
    assert (tmp_path / ".decodilo_gc_transactions" / f"{report.transaction_id}.json").exists()
    assert (tmp_path / ".decodilo_trash" / report.transaction_id).exists()


def test_gc_dry_run_deletes_nothing(tmp_path) -> None:
    _minimal_run(tmp_path)
    victim = tmp_path / "victim.tmp"
    victim.write_text("delete\n", encoding="utf-8")

    plan = plan_artifact_gc(workdir=tmp_path)

    assert victim.exists()
    assert str(victim) in plan.delete_candidates

