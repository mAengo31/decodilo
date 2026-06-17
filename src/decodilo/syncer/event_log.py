"""Deterministic append-only JSONL event log."""

from __future__ import annotations

import json
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from decodilo.errors import ReplayMismatchError
from decodilo.protocol.versions import EVENT_LOG_SCHEMA_VERSION


class EventType(str, Enum):
    LEARNER_STARTED = "learner_started"
    LEARNER_PAUSED = "learner_paused"
    LEARNER_FAILED = "learner_failed"
    LEARNER_RECOVERED = "learner_recovered"
    LEARNER_SLOWED = "learner_slowed"
    LEARNER_SPEED_RESTORED = "learner_speed_restored"
    LEARNER_UNHEALTHY = "learner_unhealthy"
    LEARNER_FRAGMENT_SUBMITTED = "learner_fragment_submitted"
    SYNC_ROUND_STARTED = "sync_round_started"
    SYNC_ROUND_COMMITTED = "sync_round_committed"
    SYNC_ROUND_SKIPPED = "sync_round_skipped"
    FRAGMENT_REJECTED = "fragment_rejected"
    CHECKPOINT_WRITTEN = "checkpoint_written"
    SYNCER_CHECKPOINT_WRITTEN = "syncer_checkpoint_written"
    SYNCER_RECOVERED = "syncer_recovered"
    LEARNER_RECONNECTED = "learner_reconnected"
    PRICE_SNAPSHOT_LOADED = "price_snapshot_loaded"
    BUDGET_LIMIT_TRIGGERED = "budget_limit_triggered"
    TRANSPORT_DUPLICATE = "transport_duplicate"
    GLOBAL_UPDATE_SENT = "global_update_sent"
    GLOBAL_UPDATE_ACKED = "global_update_acked"
    BACKPRESSURE_REJECTED = "backpressure_rejected"


class LogEvent(BaseModel):
    """A single deterministic event record."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: EventType
    schema_version: str = EVENT_LOG_SCHEMA_VERSION
    logical_time: int = Field(ge=0)
    run_id: str
    learner_id: str | None = None
    round_id: str | None = None
    fragment_id: str | None = None
    sequence: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != EVENT_LOG_SCHEMA_VERSION:
            raise ValueError(f"unknown event schema_version {value!r}")
        return value

    def to_json_line(self) -> str:
        """Serialize with stable ordering and no whitespace."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )


REQUIRED_EVENT_FIELDS = {
    "event_id",
    "event_type",
    "schema_version",
    "logical_time",
    "run_id",
    "payload",
}


def make_event_id(run_id: str, sequence: int, event_type: EventType) -> str:
    """Create a deterministic event id that is stable within a run."""

    return f"{run_id}:{sequence:08d}:{event_type.value}"


def _decode_event(line: str, *, source: str) -> LogEvent:
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ReplayMismatchError(f"invalid JSON event in {source}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ReplayMismatchError(f"event in {source} must be a JSON object")

    missing = sorted(REQUIRED_EVENT_FIELDS - raw.keys())
    if missing:
        raise ReplayMismatchError(f"event in {source} missing required fields: {missing}")

    if raw.get("schema_version") != EVENT_LOG_SCHEMA_VERSION:
        raise ReplayMismatchError(
            f"unknown event schema_version {raw.get('schema_version')!r} in {source}"
        )

    try:
        return LogEvent.model_validate(raw)
    except ValidationError as exc:
        raise ReplayMismatchError(f"invalid event in {source}: {exc}") from exc


class EventLog:
    """Append-only JSONL writer with an in-memory mirror for tests."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        truncate: bool = True,
        run_id: str = "run-default",
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.events: list[LogEvent] = []
        self._next_sequence = 0
        self.run_id = run_id
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if truncate:
                self.path.write_text("", encoding="utf-8")
            elif self.path.exists():
                existing = list(read_event_log(self.path))
                self.events.extend(existing)
                self._next_sequence = existing[-1].sequence + 1 if existing else 0
                if existing:
                    self.run_id = existing[-1].run_id

    def append(
        self,
        event_type: EventType,
        *,
        logical_time: int,
        payload: dict[str, Any] | None = None,
        learner_id: str | None = None,
        round_id: str | None = None,
        fragment_id: str | None = None,
    ) -> LogEvent:
        sequence = self._next_sequence
        event = LogEvent(
            event_id=make_event_id(self.run_id, sequence, event_type),
            event_type=event_type,
            schema_version=EVENT_LOG_SCHEMA_VERSION,
            logical_time=logical_time,
            run_id=self.run_id,
            learner_id=learner_id,
            round_id=round_id,
            fragment_id=fragment_id,
            sequence=sequence,
            payload=payload or {},
        )
        self._next_sequence += 1
        self.events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(event.to_json_line() + "\n")
        return event


def read_event_log(path: str | Path) -> Iterable[LogEvent]:
    """Read a JSONL event log in append order."""

    log_path = Path(path)
    with log_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped:
                yield _decode_event(stripped, source=f"{log_path}:{line_number}")
