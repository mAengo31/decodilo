import json
import subprocess
import sys

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest

pytestmark = [pytest.mark.storage]


def _minimal_run(tmp_path):
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    events = tmp_path / "events.jsonl"
    for path in (run_spec, report, events):
        path.write_text("{}\n", encoding="utf-8")
    manifest = build_artifact_manifest(
        run_id="reach-run",
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


def test_reachability_graph_report_cli(tmp_path) -> None:
    _minimal_run(tmp_path)
    orphan = tmp_path / "orphan.dat"
    orphan.write_text("orphan\n", encoding="utf-8")
    out = tmp_path / "reachability_graph.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "artifacts",
            "reachability",
            "--workdir",
            str(tmp_path),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["root_nodes"]
    assert str(orphan) in report["unreachable_nodes"]
    assert json.loads(out.read_text(encoding="utf-8"))["nodes"]
