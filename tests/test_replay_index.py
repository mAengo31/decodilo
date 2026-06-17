import pytest

from decodilo.syncer.replay_index import ReplayIndex, ReplayStartPoint

pytestmark = [pytest.mark.unit, pytest.mark.replay]


def test_replay_index_records_snapshot_start_point() -> None:
    index = ReplayIndex(
        run_id="run-index",
        event_log_path="events.jsonl",
        latest_snapshot_path="replay_snapshot.json",
        start_points=[
            ReplayStartPoint(
                mode="snapshot",
                snapshot_path="replay_snapshot.json",
                start_after_event_id="run-index:00000010:sync_round_committed",
                start_after_logical_time=10,
            )
        ],
    )

    assert index.start_points[0].mode == "snapshot"

