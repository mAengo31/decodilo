import asyncio

import pytest

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.transport.envelope import MessageType, make_envelope

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_idempotency_table_survives_syncer_restart(tmp_path) -> None:
    async def scenario() -> None:
        config = SyncerServiceConfig(
            run_id="run-idem-restart",
            workdir=tmp_path,
            learners=1,
            vector_dim=1,
            min_quorum=1,
        )
        service = SyncerService(config)
        submit = make_envelope(
            run_id="run-idem-restart",
            sender_id="learner-0",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="same-key",
            payload={
                "vector": [2.0],
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
            },
        )
        first = await service.handle_envelope(submit)
        service._write_syncer_checkpoint()

        recovered = SyncerService(
            SyncerServiceConfig(
                run_id="run-idem-restart",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
                recover_from_checkpoint=True,
            )
        )
        second = await recovered.handle_envelope(submit)

        assert first.payload["outcome"] == "committed"
        assert second.payload["duplicate"] is True
        assert recovered.store.metrics.useful_tokens == 10

    asyncio.run(scenario())
