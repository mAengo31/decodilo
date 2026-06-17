import json
import subprocess
import sys

import pytest

from decodilo.runtime.syncer_checkpoint import load_chunked_syncer_checkpoint

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_local_syncer_restart_recovers_and_replay_passes(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "4",
            "--steps",
            "90",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--syncer-checkpoint-interval-rounds",
            "1",
            "--restart-syncer-after-round",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=25,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    assert report["final_global_version"] >= 2
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert "syncer_recovered" in events
    assert "learner_reconnected" in events


def test_local_syncer_restart_with_chunked_checkpoints_restores_artifact(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "4",
            "--steps",
            "90",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--syncer-checkpoint-interval-rounds",
            "1",
            "--restart-syncer-after-round",
            "2",
            "--chunked-checkpoints",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    committed_versions = [
        event["payload"]["new_global_version"]
        for event in events
        if event["event_type"] == "sync_round_committed"
    ]
    restored = load_chunked_syncer_checkpoint(
        manifest_path=tmp_path / "chunked_checkpoints" / "syncer_checkpoint.artifact.json",
        chunk_store_dir=tmp_path / "chunked_checkpoints" / "store",
    )

    assert report["process_summary"]["syncer_restarts"]
    assert committed_versions == sorted(committed_versions)
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert restored.global_version == report["final_global_version"]
    assert "syncer_recovered" in (tmp_path / "events.jsonl").read_text(encoding="utf-8")
