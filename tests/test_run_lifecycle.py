import json
import subprocess
import sys

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.syncer.event_log import EventLog, EventType

pytestmark = [pytest.mark.unit, pytest.mark.replay]


def _write_valid_minimal_run(tmp_path) -> None:
    (tmp_path / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": "run-life",
                "mode": "local_multiprocess",
                "trainer_type": "numpy_convex",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "run_id": "run-life",
                "final_global_version": 0,
                "metrics": {
                    "total_tokens_processed": 0,
                    "useful_tokens_accepted": 0,
                    "wasted_tokens": 0,
                    "goodput_ratio": 0.0,
                    "committed_sync_rounds": 0,
                    "global_update_messages_sent": 0,
                    "global_update_acks": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    log = EventLog(tmp_path / "events.jsonl", run_id="run-life")
    log.append(
        EventType.CHECKPOINT_WRITTEN,
        logical_time=0,
        payload={"global_version": 0, "global_vector": [0.0]},
    )
    manifest = build_artifact_manifest(
        run_id="run-life",
        workdir=tmp_path,
        run_spec_path=tmp_path / "run_spec.json",
        report_path=tmp_path / "report.json",
        event_log_path=tmp_path / "events.jsonl",
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)


def test_run_inspect_validate_and_compact_cli(tmp_path) -> None:
    _write_valid_minimal_run(tmp_path)

    inspect = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "run", "inspect", "--workdir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    validate = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "run", "validate", "--workdir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    compact = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "run",
            "compact",
            "--workdir",
            str(tmp_path),
            "--out",
            str(tmp_path / "compact_report.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(inspect.stdout)["run_id"] == "run-life"
    assert json.loads(validate.stdout)["passed"] is True
    compact_payload = json.loads(compact.stdout)
    assert compact_payload["replay_snapshot_path"]
    assert (tmp_path / "compact_report.json").exists()
