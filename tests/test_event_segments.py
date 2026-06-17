import pytest

from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.event_segments import (
    EventSegmentReader,
    EventSegmentRotationPolicy,
    EventSegmentWriter,
)

pytestmark = [pytest.mark.unit, pytest.mark.replay]


def test_segment_rotation_by_event_count_and_chain_validation(tmp_path) -> None:
    log = EventLog(run_id="run-segments")
    events = [
        log.append(EventType.LEARNER_STARTED, logical_time=index, payload={"learner_id": "l0"})
        for index in range(3)
    ]
    writer = EventSegmentWriter(
        root=tmp_path,
        run_id="run-segments",
        policy=EventSegmentRotationPolicy(max_events_per_segment=1),
    )
    for event in events:
        writer.append(event)
    manifest = writer.finalize()

    assert len(manifest.segments) == 3
    reader = EventSegmentReader(tmp_path / "segments_manifest.json")
    assert [event.event_id for event in reader.iter_events()] == [
        event.event_id for event in events
    ]


def test_corrupted_segment_fails_validation(tmp_path) -> None:
    log = EventLog(run_id="run-segments")
    event = log.append(EventType.LEARNER_STARTED, logical_time=0, payload={"learner_id": "l0"})
    writer = EventSegmentWriter(root=tmp_path, run_id="run-segments")
    writer.append(event)
    writer.finalize()
    (tmp_path / "segment-000000.jsonl").write_text("corrupt\n", encoding="utf-8")

    with pytest.raises(Exception, match="sha256 mismatch"):
        EventSegmentReader(tmp_path / "segments_manifest.json").validate()
