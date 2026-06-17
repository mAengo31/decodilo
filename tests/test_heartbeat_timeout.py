import asyncio

import pytest

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.transport.envelope import MessageType, make_envelope

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_learner_that_stops_heartbeating_is_marked_unhealthy(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-heartbeat",
                workdir=tmp_path,
                learners=2,
                vector_dim=1,
                min_quorum=1,
                heartbeat_timeout_seconds=0.05,
                heartbeat_check_interval_seconds=0.01,
            )
        )
        await service.start()
        await service.handle_envelope(
            make_envelope(
                run_id="run-heartbeat",
                sender_id="learner-0",
                message_type=MessageType.REGISTER_LEARNER,
                payload={"learner_id": "learner-0"},
            )
        )
        await asyncio.sleep(0.09)
        await service.stop()
        await service.server.close()
        assert "learner-0" in service.unhealthy_learners

    asyncio.run(scenario())
