from __future__ import annotations

import asyncio

from decodilo.transport.tcp_server import JsonlTcpServer


def test_tcp_server_close_closes_active_idle_clients() -> None:
    async def scenario() -> None:
        async def handler(_envelope):
            return None

        server = JsonlTcpServer(handler=handler, timeout_seconds=30.0)
        await server.start()
        reader, writer = await asyncio.open_connection(server.bound_host, server.bound_port)
        for _ in range(20):
            if server._active_writers:
                break
            await asyncio.sleep(0.01)
        assert server._active_writers
        assert not reader.at_eof()

        await asyncio.wait_for(server.close(), timeout=1.0)

        assert await asyncio.wait_for(reader.read(1), timeout=1.0) == b""
        writer.close()
        await writer.wait_closed()

    asyncio.run(scenario())
