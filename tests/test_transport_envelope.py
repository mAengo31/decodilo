import pytest

from decodilo.transport.envelope import MessageType, TransportEnvelope, make_envelope
from decodilo.transport.errors import MalformedMessageError, UnknownMessageTypeError


def test_valid_envelope_serializes_and_deserializes() -> None:
    envelope = make_envelope(
        run_id="run-1",
        sender_id="learner-0",
        recipient_id="syncer",
        message_type=MessageType.HEARTBEAT,
        payload={"tokens": 10},
        message_id="m-1",
    )

    decoded = TransportEnvelope.from_json_line(envelope.to_json_line())

    assert decoded == envelope


def test_missing_required_fields_are_rejected() -> None:
    with pytest.raises(MalformedMessageError):
        TransportEnvelope.from_json_line('{"schema_version":"v1"}')


def test_unknown_schema_version_is_rejected() -> None:
    with pytest.raises(MalformedMessageError):
        TransportEnvelope.from_json_line(
            '{"schema_version":"v2","message_id":"m","run_id":"r","sender_id":"s",'
            '"message_type":"heartbeat","payload":{}}'
        )


def test_submit_fragment_without_idempotency_key_is_rejected() -> None:
    with pytest.raises(MalformedMessageError):
        make_envelope(
            run_id="run-1",
            sender_id="learner-0",
            message_type=MessageType.SUBMIT_FRAGMENT,
            payload={"tokens": 1},
        )


def test_unknown_message_type_is_rejected() -> None:
    with pytest.raises(UnknownMessageTypeError):
        TransportEnvelope.from_json_line(
            '{"schema_version":"v1","message_id":"m","run_id":"r","sender_id":"s",'
            '"message_type":"bogus","payload":{}}'
        )


def test_stable_json_serialization_is_deterministic() -> None:
    envelope = make_envelope(
        run_id="run-1",
        sender_id="a",
        message_type=MessageType.HEARTBEAT,
        payload={"b": 2, "a": 1},
        message_id="msg",
    )

    assert envelope.to_json_line() == envelope.to_json_line()
    assert envelope.to_json_line() == (
        '{"created_logical_time":null,"idempotency_key":null,"message_id":"msg",'
        '"message_type":"heartbeat","payload":{"a":1,"b":2},"recipient_id":null,'
        '"run_id":"run-1","schema_version":"v1","sender_id":"a"}'
    )

