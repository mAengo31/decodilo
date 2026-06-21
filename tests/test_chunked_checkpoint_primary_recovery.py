import json
import subprocess
import sys

import pytest

from decodilo.runtime.syncer_checkpoint import load_chunked_syncer_checkpoint
from decodilo.syncer.recovery_manifest import load_recovery_manifest

pytestmark = pytest.mark.integration


def test_chunked_checkpoint_is_primary_live_recovery_source(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "70",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--payload-storage-mode",
            "chunked",
            "--global-update-storage-mode",
            "chunked",
            "--checkpoint-storage-mode",
            "chunked",
            "--merge-mode",
            "streaming_chunked",
            "--chunk-size-mb",
            "1",
            "--memory-budget-mb",
            "1",
            "--allow-spill-to-disk",
            "--syncer-checkpoint-interval-rounds",
            "1",
            "--restart-syncer-after-round",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=35,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    recovered = [event for event in events if event["event_type"] == "syncer_recovered"]
    committed_versions = [
        event["payload"]["new_global_version"]
        for event in events
        if event["event_type"] == "sync_round_committed"
    ]
    recovery_manifest = load_recovery_manifest(tmp_path / "recovery_manifest.json")
    checkpoint_manifest = recovery_manifest.checkpoint_ref["manifest_path"]
    checkpoint = load_chunked_syncer_checkpoint(
        manifest_path=checkpoint_manifest,
        chunk_store_dir=tmp_path / "live_checkpoints" / "store",
    )

    assert not (tmp_path / "syncer_checkpoint.json").exists()
    assert report["recovery_source"] == "chunked"
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert recovered
    assert recovered[-1]["payload"]["recovery_source"] == "chunked"
    assert recovered[-1]["payload"]["checkpoint_artifact_ref"] is not None
    assert committed_versions == sorted(committed_versions)
    assert checkpoint.global_version <= report["final_global_version"]
