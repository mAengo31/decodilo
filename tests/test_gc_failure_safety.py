import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.runtime.run_lifecycle import validate_run
from decodilo.storage.gc_transaction import apply_gc_transaction

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def _minimal_run(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-fail",
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


def test_partial_delete_failure_leaves_failed_transaction_detected_by_validate(tmp_path) -> None:
    _minimal_run(tmp_path)
    first = tmp_path / "first.tmp"
    second = tmp_path / "second.tmp"
    first.write_text("first\n", encoding="utf-8")
    second.write_text("second\n", encoding="utf-8")

    with pytest.raises(Exception, match="gc transaction failed"):
        apply_gc_transaction(
            workdir=tmp_path,
            planned_deletes=[str(first), str(second)],
            fail_after=1,
        )

    validation = validate_run(tmp_path, replay=False)
    assert validation.passed is False
    assert any("failed gc transaction" in error for error in validation.errors)


def test_gc_refuses_artifact_that_became_reachable_after_plan(tmp_path) -> None:
    _minimal_run(tmp_path)
    victim = tmp_path / "victim.tmp"
    victim.write_text("keep\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="run-fail",
        workdir=tmp_path,
        run_spec_path=tmp_path / "run_spec.json",
        report_path=tmp_path / "report.json",
        event_log_path=tmp_path / "events.jsonl",
        syncer_checkpoint_paths=[victim],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)

    tx = apply_gc_transaction(workdir=tmp_path, planned_deletes=[str(victim)])

    assert str(victim) in tx.skipped_protected
    assert victim.exists()
