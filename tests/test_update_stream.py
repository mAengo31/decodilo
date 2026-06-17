import asyncio

import pytest

from decodilo.errors import ReplayMismatchError
from decodilo.runtime.update_stream import UpdateStream
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.replay import replay_event_log


def test_update_stream_long_poll_and_ack_reduces_lag() -> None:
    async def scenario() -> None:
        stream = UpdateStream(max_version_lag=1)
        stream.register("learner-0", version=0)

        assert not await stream.wait_for_update(
            learner_id="learner-0",
            learner_version=0,
            current_version=0,
            timeout_seconds=0.001,
        )

        stream.notify_commit(global_version=1)
        assert await stream.wait_for_update(
            learner_id="learner-0",
            learner_version=0,
            current_version=1,
            timeout_seconds=0.001,
        )
        stream.mark_sent("learner-0", global_version=1)
        stream.ack("learner-0", global_version=1, current_version=1)

        assert stream.metrics.global_update_broadcasts == 1
        assert stream.metrics.global_update_messages_sent == 1
        assert stream.metrics.global_update_acks == 1
        assert stream.learner_update_lag_current == {"learner-0": 0}
        assert stream.metrics.learner_update_lag_max == 1
        assert stream.stale_learners(current_version=3) == {"learner-0"}

    asyncio.run(scenario())


def test_replay_rejects_update_ack_for_future_version(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl", run_id="run-update-replay")
    log.append(
        EventType.GLOBAL_UPDATE_ACKED,
        logical_time=0,
        learner_id="learner-0",
        payload={"learner_id": "learner-0", "global_version": 1},
    )

    with pytest.raises(ReplayMismatchError, match="future global_version"):
        replay_event_log(tmp_path / "events.jsonl")
