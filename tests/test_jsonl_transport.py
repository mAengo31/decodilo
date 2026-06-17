import asyncio

import pytest

from decodilo.transport.envelope import MessageType, make_envelope
from decodilo.transport.jsonl import decode_envelope_line
from decodilo.transport.tcp_client import JsonlTcpClient
from decodilo.transport.tcp_server import JsonlTcpServer

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_client_server_can_exchange_envelopes() -> None:
    async def scenario() -> None:
        async def handler(envelope):
            return make_envelope(
                run_id=envelope.run_id,
                sender_id="server",
                recipient_id=envelope.sender_id,
                message_type=MessageType.HEARTBEAT_ACK,
                payload={"ok": True},
                message_id="ack",
            )

        server = JsonlTcpServer(handler=handler, run_id="run-1")
        await server.start()
        assert server.bound_port is not None
        async with JsonlTcpClient(host="127.0.0.1", port=server.bound_port) as client:
            response = await client.request(
                make_envelope(
                    run_id="run-1",
                    sender_id="client",
                    message_type=MessageType.HEARTBEAT,
                    payload={},
                )
            )
        await server.close()
        assert response.message_type == MessageType.HEARTBEAT_ACK
        assert response.payload == {"ok": True}

    asyncio.run(scenario())


def test_malformed_json_is_rejected_without_crashing_server() -> None:
    async def scenario() -> None:
        async def handler(envelope):
            return make_envelope(
                run_id=envelope.run_id,
                sender_id="server",
                message_type=MessageType.HEARTBEAT_ACK,
            )

        server = JsonlTcpServer(handler=handler, run_id="run-1")
        await server.start()
        assert server.bound_port is not None
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        writer.write(b"{bad-json}\n")
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
        await server.close()
        response = decode_envelope_line(line)
        assert response.message_type == MessageType.ERROR

    asyncio.run(scenario())


def test_oversized_message_is_rejected() -> None:
    async def scenario() -> None:
        async def handler(envelope):
            return make_envelope(
                run_id=envelope.run_id,
                sender_id="server",
                message_type=MessageType.HEARTBEAT_ACK,
            )

        server = JsonlTcpServer(handler=handler, run_id="run-1", max_message_bytes=20)
        await server.start()
        assert server.bound_port is not None
        reader, writer = await asyncio.open_connection("127.0.0.1", server.bound_port)
        writer.write(b'{"this":"message is too large"}\n')
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
        await server.close()
        response = decode_envelope_line(line)
        assert response.message_type == MessageType.ERROR
        assert response.payload["error_type"] == "OversizedMessageError"

    asyncio.run(scenario())


def test_multiple_clients_can_connect() -> None:
    async def scenario() -> None:
        async def handler(envelope):
            return make_envelope(
                run_id=envelope.run_id,
                sender_id="server",
                recipient_id=envelope.sender_id,
                message_type=MessageType.HEARTBEAT_ACK,
                payload={"sender": envelope.sender_id},
            )

        server = JsonlTcpServer(handler=handler, run_id="run-1")
        await server.start()
        assert server.bound_port is not None

        async def one(sender):
            async with JsonlTcpClient(host="127.0.0.1", port=server.bound_port) as client:
                return await client.request(
                    make_envelope(
                        run_id="run-1",
                        sender_id=sender,
                        message_type=MessageType.HEARTBEAT,
                    )
                )

        responses = await asyncio.gather(one("a"), one("b"), one("c"))
        await server.close()
        assert {response.payload["sender"] for response in responses} == {"a", "b", "c"}

    asyncio.run(scenario())


def test_server_shuts_down_cleanly() -> None:
    async def scenario() -> None:
        async def handler(envelope):
            return None

        server = JsonlTcpServer(handler=handler)
        await server.start()
        await server.close()
        assert server.server is None

    asyncio.run(scenario())
