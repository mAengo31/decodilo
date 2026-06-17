import asyncio

import numpy as np

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.syncer.replay import replay_event_log
from decodilo.transport.envelope import MessageType, make_envelope


def test_duplicate_fragment_submission_does_not_double_count_tokens(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-idempotency",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
            )
        )
        await service.start()
        vector = np.array([2.0])
        submit = make_envelope(
            run_id="run-idempotency",
            sender_id="learner-0",
            recipient_id="syncer",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="same-key",
            payload={
                "vector": vector.tolist(),
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
            },
        )
        first = await service.handle_envelope(submit)
        second = await service.handle_envelope(submit)
        await service.handle_envelope(
            make_envelope(
                run_id="run-idempotency",
                sender_id="supervisor",
                message_type=MessageType.SYNCER_SHUTDOWN,
            )
        )
        await service.server.close()
        assert first.payload["outcome"] == "committed"
        assert second.payload["duplicate"] is True
        assert service.store.metrics.useful_tokens == 10
        np.testing.assert_allclose(service.store.global_vector, np.array([2.0]))
        replayed = replay_event_log(tmp_path / "events.jsonl")
        assert replayed.accepted_useful_tokens == 10

    asyncio.run(scenario())

