"""Versioned transport envelope for local process messages."""

from __future__ import annotations

import json
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from decodilo.transport.errors import MalformedMessageError, UnknownMessageTypeError

TRANSPORT_SCHEMA_VERSION = "v1"


class MessageType(str, Enum):
    REGISTER_LEARNER = "register_learner"
    REGISTER_LEARNER_ACK = "register_learner_ack"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    REQUEST_GLOBAL_STATE = "request_global_state"
    GLOBAL_STATE_RESPONSE = "global_state_response"
    SUBMIT_FRAGMENT = "submit_fragment"
    SUBMIT_FRAGMENT_ACK = "submit_fragment_ack"
    SUBMIT_FRAGMENT_REJECTED = "submit_fragment_rejected"
    SYNC_ROUND_COMMITTED = "sync_round_committed"
    SUBSCRIBE_UPDATES = "subscribe_updates"
    SUBSCRIBE_UPDATES_ACK = "subscribe_updates_ack"
    GLOBAL_UPDATE_AVAILABLE = "global_update_available"
    GLOBAL_UPDATE_PAYLOAD = "global_update_payload"
    GLOBAL_UPDATE_ACK = "global_update_ack"
    FETCH_ARTIFACT = "fetch_artifact"
    FETCH_ARTIFACT_RESPONSE = "fetch_artifact_response"
    BACKPRESSURE_WARNING = "backpressure_warning"
    BACKPRESSURE_REJECT = "backpressure_reject"
    LEARNER_SHUTDOWN = "learner_shutdown"
    SYNCER_SHUTDOWN = "syncer_shutdown"
    ERROR = "error"


class TransportEnvelope(BaseModel):
    """Validated message envelope for JSONL-over-TCP transport."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = TRANSPORT_SCHEMA_VERSION
    message_id: str
    run_id: str
    sender_id: str
    recipient_id: str | None = None
    message_type: MessageType
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_logical_time: int | None = Field(default=None, ge=0)

    @field_validator("schema_version")
    @classmethod
    def _schema_is_known(cls, value: str) -> str:
        if value != TRANSPORT_SCHEMA_VERSION:
            raise ValueError(f"unknown transport schema_version {value!r}")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def _submit_fragment_requires_idempotency(
        cls,
        value: str | None,
        info,
    ) -> str | None:
        message_type = info.data.get("message_type")
        if message_type == MessageType.SUBMIT_FRAGMENT and not value:
            raise ValueError("submit_fragment requires idempotency_key")
        return value

    def to_json_line(self) -> str:
        """Return deterministic JSONL serialization."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json_line(cls, line: str) -> TransportEnvelope:
        """Decode and validate a JSON object line."""

        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MalformedMessageError(f"malformed JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise MalformedMessageError("transport envelope must be a JSON object")
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            if "message_type" in raw and any(
                error.get("loc") == ("message_type",) for error in exc.errors()
            ):
                raise UnknownMessageTypeError(str(exc)) from exc
            raise MalformedMessageError(str(exc)) from exc


def new_message_id(sender_id: str) -> str:
    """Create a process-local unique message id."""

    return f"{sender_id}:{uuid.uuid4().hex}"


def make_envelope(
    *,
    run_id: str,
    sender_id: str,
    message_type: MessageType,
    payload: dict[str, Any] | None = None,
    recipient_id: str | None = None,
    idempotency_key: str | None = None,
    message_id: str | None = None,
    created_logical_time: int | None = None,
) -> TransportEnvelope:
    """Convenience constructor with a generated message id."""

    try:
        return TransportEnvelope(
            schema_version=TRANSPORT_SCHEMA_VERSION,
            message_id=message_id or new_message_id(sender_id),
            run_id=run_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            idempotency_key=idempotency_key,
            payload=payload or {},
            created_logical_time=created_logical_time,
        )
    except ValidationError as exc:
        raise MalformedMessageError(str(exc)) from exc
