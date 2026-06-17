import numpy as np
import pytest

from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.event_segments import segment_events_from_jsonl
from decodilo.syncer.replay import replay_event_log
from decodilo.syncer.replay_snapshot import (
    load_replay_snapshot,
    make_replay_snapshot,
    replay_from_snapshot_and_segments,
    write_replay_snapshot,
)

pytestmark = [pytest.mark.unit, pytest.mark.replay]


def test_snapshot_replay_matches_genesis_and_reads_tail(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl", run_id="run-snapshot")
    first = event_log.append(
        EventType.LEARNER_STARTED,
        logical_time=0,
        learner_id="learner-0",
        payload={"learner_id": "learner-0"},
    )
    event_log.append(
        EventType.CHECKPOINT_WRITTEN,
        logical_time=1,
        payload={"global_version": 0, "global_vector": [0.0]},
    )
    segment_events_from_jsonl(
        event_log_path=tmp_path / "events.jsonl",
        out_dir=tmp_path / "event_segments",
    )
    snapshot = make_replay_snapshot(
        run_id="run-snapshot",
        global_version=0,
        logical_time=0,
        last_event_id=first.event_id,
        committed_rounds=0,
        useful_tokens_accepted=0,
        global_vector=np.asarray([0.0]),
    )
    write_replay_snapshot(tmp_path / "replay_snapshot.json", snapshot)

    genesis = replay_event_log(tmp_path / "events.jsonl")
    from_snapshot = replay_from_snapshot_and_segments(
        snapshot_path=tmp_path / "replay_snapshot.json",
        segment_manifest_path=tmp_path / "event_segments" / "segments_manifest.json",
        artifact_workdir=tmp_path,
    )

    assert from_snapshot.accepted_useful_tokens == genesis.accepted_useful_tokens
    assert from_snapshot.global_versions == genesis.global_versions


def test_corrupted_snapshot_fails(tmp_path) -> None:
    snapshot = make_replay_snapshot(
        run_id="run-snapshot",
        global_version=0,
        logical_time=0,
        last_event_id="run-snapshot:00000000:learner_started",
        committed_rounds=0,
        useful_tokens_accepted=0,
        global_vector=np.asarray([0.0]),
    )
    write_replay_snapshot(tmp_path / "replay_snapshot.json", snapshot)
    data = (tmp_path / "replay_snapshot.json").read_text(encoding="utf-8")
    (tmp_path / "replay_snapshot.json").write_text(data.replace("0.0", "1.0"), encoding="utf-8")

    with pytest.raises(Exception, match="snapshot"):
        load_replay_snapshot(tmp_path / "replay_snapshot.json")

