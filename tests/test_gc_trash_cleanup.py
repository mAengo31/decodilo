import json
import subprocess
import sys

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.storage.gc import run_artifact_gc
from decodilo.storage.gc_cleanup import cleanup_gc_trash
from decodilo.storage.trash_lifecycle import inspect_trash

pytestmark = [pytest.mark.lifecycle, pytest.mark.storage]


def _minimal_run(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="trash-run",
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


def test_gc_trash_cleanup_dry_run_apply_and_resume(tmp_path) -> None:
    _minimal_run(tmp_path)
    victim = tmp_path / "victim.tmp"
    victim.write_text("delete\n", encoding="utf-8")
    gc_report = run_artifact_gc(workdir=tmp_path, apply=True)
    trash_dir = tmp_path / ".decodilo_trash" / gc_report.transaction_id

    dry = cleanup_gc_trash(workdir=tmp_path, apply=False)
    assert dry.dry_run is True
    assert trash_dir.exists()
    applied = cleanup_gc_trash(workdir=tmp_path, apply=True)
    resumed = cleanup_gc_trash(workdir=tmp_path, apply=True)

    assert applied.bytes_purged > 0
    assert not trash_dir.exists()
    assert resumed.bytes_purged == 0


def test_trash_inspect_and_cleanup_cli(tmp_path) -> None:
    _minimal_run(tmp_path)
    victim = tmp_path / "victim.tmp"
    victim.write_text("delete\n", encoding="utf-8")
    run_artifact_gc(workdir=tmp_path, apply=True)

    inspect = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "artifacts",
            "trash",
            "inspect",
            "--workdir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    cleanup = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "artifacts",
            "trash",
            "cleanup",
            "--workdir",
            str(tmp_path),
            "--apply",
            "--out",
            str(tmp_path / "trash_cleanup_report.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(inspect.stdout)["entries"]
    assert json.loads(cleanup.stdout)["bytes_purged"] > 0
    assert inspect_trash(tmp_path).entries

