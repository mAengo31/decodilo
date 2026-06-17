"""Transport-specific failures for local JSONL-over-TCP runtime."""

from decodilo.errors import DecodiloError


class TransportError(DecodiloError):
    """Base transport error."""


class MalformedMessageError(TransportError):
    """Raised when a JSONL message cannot be decoded or validated."""


class OversizedMessageError(TransportError):
    """Raised when a JSONL message exceeds the configured size limit."""


class UnknownMessageTypeError(TransportError):
    """Raised when a message_type is not part of the v1 transport protocol."""


class TransportTimeoutError(TransportError):
    """Raised when a transport read or write exceeds its timeout."""

