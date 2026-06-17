import asyncio

import pytest

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.syncer.replay import replay_event_log
from decodilo.transport.envelope import MessageType, make_envelope
from decodilo.transport.jsonl import read_envelope
from decodilo.transport.tcp_client import JsonlTcpClient

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_retry_reorder_duplicate_ack_and_malformed_message_do_not_corrupt_run(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-retry-reorder",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
                update_long_poll_timeout_seconds=0.001,
            )
        )
        await service.start()
        assert service.server.bound_host is not None
        assert service.server.bound_port is not None

        reader, writer = await asyncio.open_connection(
            service.server.bound_host,
            service.server.bound_port,
        )
        writer.write(b"{not-json}\n")
        await writer.drain()
        error = await read_envelope(reader)
        writer.close()
        await writer.wait_closed()
        assert error.message_type == MessageType.ERROR

        async with JsonlTcpClient(
            host=service.server.bound_host,
            port=service.server.bound_port,
            timeout_seconds=1.0,
        ) as client:
            await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="learner-0",
                    message_type=MessageType.REGISTER_LEARNER,
                    payload={"learner_id": "learner-0"},
                )
            )
            await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="learner-0",
                    message_type=MessageType.GLOBAL_UPDATE_ACK,
                    payload={"global_version": 0},
                )
            )
            await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="learner-0",
                    message_type=MessageType.GLOBAL_UPDATE_ACK,
                    payload={"global_version": 0},
                )
            )
            submit = make_envelope(
                run_id="run-retry-reorder",
                sender_id="learner-0",
                message_type=MessageType.SUBMIT_FRAGMENT,
                idempotency_key="retry-key",
                payload={
                    "vector": [2.0],
                    "global_version_seen": 0,
                    "tokens": 10,
                    "tokens_processed": 10,
                },
            )
            first = await client.request(submit)
            second = await client.request(submit)
            await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="learner-0",
                    message_type=MessageType.HEARTBEAT,
                    payload={"tokens_processed": 10},
                )
            )
            await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="learner-0",
                    message_type=MessageType.REGISTER_LEARNER,
                    payload={"learner_id": "learner-0"},
                )
            )
            shutdown = await client.request(
                make_envelope(
                    run_id="run-retry-reorder",
                    sender_id="supervisor",
                    message_type=MessageType.SYNCER_SHUTDOWN,
                )
            )

        await service.server.close()
        assert first.payload["outcome"] == "committed"
        assert second.payload["duplicate"] is True
        assert service.store.metrics.useful_tokens == 10
        assert shutdown.payload["metrics"]["duplicate_global_update_acks"] >= 2
        assert shutdown.payload["metrics"]["global_update_acks"] == 0
        replay = replay_event_log(tmp_path / "events.jsonl")
        assert replay.accepted_useful_tokens == 10

    asyncio.run(scenario())
