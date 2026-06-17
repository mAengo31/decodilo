"""JSONL framing helpers for asyncio streams."""

from __future__ import annotations

import asyncio

from decodilo.transport.envelope import MessageType, TransportEnvelope, make_envelope
from decodilo.transport.errors import (
    MalformedMessageError,
    OversizedMessageError,
    TransportTimeoutError,
)

DEFAULT_MAX_MESSAGE_BYTES = 1_000_000
DEFAULT_TIMEOUT_SECONDS = 5.0


def decode_envelope_line(
    line: bytes | str,
    *,
    max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
) -> TransportEnvelope:
    """Decode one UTF-8 JSONL envelope."""

    raw = line.encode("utf-8") if isinstance(line, str) else line
    if len(raw) > max_message_bytes:
        raise OversizedMessageError("transport message exceeded max_message_bytes")
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise MalformedMessageError(f"message is not UTF-8: {exc}") from exc
    if not text:
        raise MalformedMessageError("empty transport message")
    return TransportEnvelope.from_json_line(text)


def encode_envelope(envelope: TransportEnvelope) -> bytes:
    """Encode one envelope as UTF-8 JSONL bytes."""

    return (envelope.to_json_line() + "\n").encode("utf-8")


async def read_envelope(
    reader: asyncio.StreamReader,
    *,
    max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> TransportEnvelope:
    """Read one envelope from an asyncio stream."""

    try:
        line = await asyncio.wait_for(
            reader.readline(),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise TransportTimeoutError("timed out reading transport message") from exc
    if not line:
        raise TransportTimeoutError("transport stream closed")
    return decode_envelope_line(line, max_message_bytes=max_message_bytes)


async def write_envelope(
    writer: asyncio.StreamWriter,
    envelope: TransportEnvelope,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Write one envelope to an asyncio stream."""

    writer.write(encode_envelope(envelope))
    try:
        await asyncio.wait_for(writer.drain(), timeout=timeout_seconds)
    except TimeoutError as exc:
        raise TransportTimeoutError("timed out writing transport message") from exc


def error_envelope(
    *,
    run_id: str,
    sender_id: str,
    error: Exception | str,
    recipient_id: str | None = None,
) -> TransportEnvelope:
    """Create a transport-level error response."""

    return make_envelope(
        run_id=run_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        message_type=MessageType.ERROR,
        payload={"error": str(error)},
    )

