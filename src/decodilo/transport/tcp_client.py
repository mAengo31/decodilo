"""Async localhost JSONL-over-TCP client."""

from __future__ import annotations

import asyncio
from types import TracebackType

from decodilo.transport.envelope import TransportEnvelope
from decodilo.transport.jsonl import DEFAULT_MAX_MESSAGE_BYTES, read_envelope, write_envelope


class JsonlTcpClient:
    """Small request/response JSONL client for local runtime messages."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.max_message_bytes = max_message_bytes
        self.timeout_seconds = timeout_seconds
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def connect(self) -> JsonlTcpClient:
        self.reader, self.writer = await asyncio.open_connection(
            self.host,
            self.port,
            limit=self.max_message_bytes + 1,
        )
        return self

    async def close(self) -> None:
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None

    async def request(self, envelope: TransportEnvelope) -> TransportEnvelope:
        if self.reader is None or self.writer is None:
            await self.connect()
        assert self.reader is not None
        assert self.writer is not None
        await write_envelope(self.writer, envelope, timeout_seconds=self.timeout_seconds)
        return await read_envelope(
            self.reader,
            max_message_bytes=self.max_message_bytes,
            timeout_seconds=self.timeout_seconds,
        )

    async def __aenter__(self) -> JsonlTcpClient:
        return await self.connect()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
