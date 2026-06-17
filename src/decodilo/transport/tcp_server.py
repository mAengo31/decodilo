"""Async localhost JSONL-over-TCP server."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from decodilo.transport.envelope import MessageType, TransportEnvelope, make_envelope
from decodilo.transport.errors import MalformedMessageError, OversizedMessageError, TransportError
from decodilo.transport.jsonl import DEFAULT_MAX_MESSAGE_BYTES, read_envelope, write_envelope

EnvelopeHandler = Callable[[TransportEnvelope], Awaitable[TransportEnvelope | None]]


class JsonlTcpServer:
    """Minimal JSONL-over-TCP server with one response per envelope."""

    def __init__(
        self,
        *,
        handler: EnvelopeHandler,
        host: str = "127.0.0.1",
        port: int = 0,
        server_id: str = "syncer",
        run_id: str = "run-default",
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.handler = handler
        self.host = host
        self.port = port
        self.server_id = server_id
        self.run_id = run_id
        self.max_message_bytes = max_message_bytes
        self.timeout_seconds = timeout_seconds
        self.server: asyncio.AbstractServer | None = None
        self.bound_host: str | None = None
        self.bound_port: int | None = None

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        sockets = self.server.sockets or []
        if not sockets:
            raise TransportError("server did not expose a bound socket")
        sockname = sockets[0].getsockname()
        self.bound_host = str(sockname[0])
        self.bound_port = int(sockname[1])

    async def serve_forever(self) -> None:
        if self.server is None:
            await self.start()
        assert self.server is not None
        async with self.server:
            await self.server.serve_forever()

    async def close(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            while not reader.at_eof():
                try:
                    envelope = await read_envelope(
                        reader,
                        max_message_bytes=self.max_message_bytes,
                        timeout_seconds=self.timeout_seconds,
                    )
                    response = await self.handler(envelope)
                except (MalformedMessageError, OversizedMessageError, TransportError) as exc:
                    response = make_envelope(
                        run_id=self.run_id,
                        sender_id=self.server_id,
                        message_type=MessageType.ERROR,
                        payload={"error": str(exc), "error_type": exc.__class__.__name__},
                    )
                if response is not None:
                    await write_envelope(
                        writer,
                        response,
                        timeout_seconds=self.timeout_seconds,
                    )
        finally:
            writer.close()
            await writer.wait_closed()

