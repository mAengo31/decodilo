import numpy as np
import pytest

from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.event_segments import (
    EventSegmentReader,
    EventSegmentRotationPolicy,
    EventSegmentWriter,
)
from decodilo.syncer.replay_snapshot import (
    make_replay_snapshot,
    replay_from_snapshot_and_segments,
    write_replay_snapshot,
)

pytestmark = [pytest.mark.lifecycle, pytest.mark.replay]


def test_long_segment_chain_and_snapshot_tail_replay(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl", run_id="run-segments-long")
    events = [
        log.append(
            EventType.LEARNER_STARTED,
            logical_time=index,
            payload={"learner_id": f"learner-{index}"},
        )
        for index in range(25)
    ]
    writer = EventSegmentWriter(
        root=tmp_path / "event_segments",
        run_id="run-segments-long",
        policy=EventSegmentRotationPolicy(max_events_per_segment=2),
    )
    for event in events:
        writer.append(event)
    manifest = writer.finalize()
    snapshot = make_replay_snapshot(
        run_id="run-segments-long",
        global_version=0,
        logical_time=20,
        last_event_id=events[20].event_id,
        committed_rounds=0,
        useful_tokens_accepted=0,
        global_vector=np.asarray([0.0]),
    )
    write_replay_snapshot(tmp_path / "replay_snapshot.json", snapshot)

    reader = EventSegmentReader(tmp_path / "event_segments" / "segments_manifest.json")
    reader.validate()
    tail = replay_from_snapshot_and_segments(
        snapshot_path=tmp_path / "replay_snapshot.json",
        segment_manifest_path=tmp_path / "event_segments" / "segments_manifest.json",
        artifact_workdir=tmp_path,
    )

    assert len(manifest.segments) >= 10
    assert tail.accepted_useful_tokens == 0


def test_post_snapshot_segment_deletion_fails(tmp_path) -> None:
    log = EventLog(run_id="run-delete-segment")
    writer = EventSegmentWriter(
        root=tmp_path,
        run_id="run-delete-segment",
        policy=EventSegmentRotationPolicy(max_events_per_segment=1),
    )
    for index in range(3):
        writer.append(
            log.append(EventType.LEARNER_STARTED, logical_time=index, payload={"learner_id": "l"})
        )
    writer.finalize()
    (tmp_path / "segment-000002.jsonl").unlink()

    with pytest.raises(Exception, match="missing event segment"):
        EventSegmentReader(tmp_path / "segments_manifest.json").validate()
