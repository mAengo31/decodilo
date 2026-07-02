from __future__ import annotations

import asyncio

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.transport.envelope import MessageType, make_envelope


def test_syncer_shutdown_can_request_immediate_server_close(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-shutdown-immediate",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
            )
        )
        await service.start()
        response = await service.handle_envelope(
            make_envelope(
                run_id="run-shutdown-immediate",
                sender_id="pathway-restart-supervisor",
                recipient_id="syncer",
                message_type=MessageType.SYNCER_SHUTDOWN,
                payload={"immediate_server_close": True},
            )
        )
        await asyncio.sleep(0)

        assert response.message_type == MessageType.SYNCER_SHUTDOWN
        assert service.stop_event.is_set()
        assert service.server.server is None

    asyncio.run(scenario())
