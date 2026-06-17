import json

import pytest

from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.runtime.run_lifecycle import compact_run, validate_run
from decodilo.syncer.event_log import EventLog, EventType

pytestmark = [pytest.mark.lifecycle, pytest.mark.replay]


def _run(tmp_path) -> None:
    run_spec = tmp_path / "run_spec.json"
    report = tmp_path / "report.json"
    run_spec.write_text('{"run_id":"run-corrupt"}\n', encoding="utf-8")
    report.write_text(
        json.dumps(
            {
                "run_id": "run-corrupt",
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
    log = EventLog(tmp_path / "events.jsonl", run_id="run-corrupt")
    log.append(
        EventType.CHECKPOINT_WRITTEN,
        logical_time=0,
        payload={"global_version": 0, "global_vector": [0.0]},
    )
    manifest = build_artifact_manifest(
        run_id="run-corrupt",
        workdir=tmp_path,
        run_spec_path=run_spec,
        report_path=report,
        event_log_path=tmp_path / "events.jsonl",
        syncer_checkpoint_paths=[],
        learner_checkpoint_paths=[],
        learner_log_paths=[],
        price_snapshot_paths=[],
    )
    write_artifact_manifest(tmp_path / "artifacts.json", manifest)
    compact_run(tmp_path, out=tmp_path / "compact_report.json")


def test_run_validate_catches_corrupted_replay_snapshot(tmp_path) -> None:
    _run(tmp_path)
    (tmp_path / "replay_snapshot.json").write_text("not-json\n", encoding="utf-8")

    result = validate_run(tmp_path)

    assert result.passed is False
    assert any("replay_snapshot" in error for error in result.errors)


def test_run_validate_catches_corrupted_event_segment(tmp_path) -> None:
    _run(tmp_path)
    segment = next((tmp_path / "event_segments").glob("segment-*.jsonl"))
    segment.write_text("corrupt\n", encoding="utf-8")

    result = validate_run(tmp_path)

    assert result.passed is False
    assert any("event segment" in error for error in result.errors)
